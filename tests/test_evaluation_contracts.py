"""Discovery contracts used by the disconnected evaluation fixtures."""

import json
import re
import sys
import unittest
from importlib import metadata
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from cavi_character_animator_mcp import server
from evals.run import background_manifest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = {
    "character_status", "inspect", "capture", "session_control", "project_prepare_copy",
    "project_open_prepared_copy", "project_save_copy", "import_media", "scene_action",
    "scene_export", "project_select", "operation_control", "export_inspect", "export_ingest",
}


def parameters():
    return StdioServerParameters(command=sys.executable, args=[str(ROOT / "evals/simulated_server.py")])


class PackageTest(unittest.TestCase):
    def test_installs_no_other_application_server(self):
        required = {re.split(r"[^A-Za-z0-9._-]", line, maxsplit=1)[0]
                    for line in metadata.requires("cavi-character-animator-mcp")}
        self.assertNotIn("cavi-adobe-mcp", required)
        self.assertIn("cavi-mcp-core", required)


class EvaluationDescriptionTests(unittest.IsolatedAsyncioTestCase):
    async def test_registers_the_documented_tools(self):
        self.assertEqual({tool.name for tool in await server.mcp.list_tools()}, TOOLS)

    async def test_prepared_copy_description_names_the_open_tool(self):
        tools = {tool.name: tool for tool in await server.mcp.list_tools()}
        description = tools["project_prepare_copy"].description
        self.assertIn("project_open_prepared_copy", description)
        self.assertNotIn("session_control to open", description)


class BackgroundManifestTests(unittest.TestCase):
    def test_inspection_manifest_reads_only_background_tools(self):
        background_manifest(json.loads(
            (ROOT / "evals/character_animator.inspection.manifest.json").read_text()))

    def test_a_tool_that_touches_the_application_is_refused_before_server_start(self):
        manifest = {"probes": [{"probe": "output-schema", "access": "read_only",
                                "tool": "project_save_copy", "arguments": {}}]}
        with self.assertRaisesRegex(ValueError, "background tool"):
            background_manifest(manifest)


class SimulatedProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_unknown_arguments_are_rejected_at_the_mcp_boundary(self):
        async with stdio_client(parameters()) as (reader, writer), \
                ClientSession(reader, writer) as client:
            await client.initialize()
            rejected = await client.call_tool("character_status", {"unknown_setting": True})
            self.assertTrue(rejected.is_error, "Unknown arguments must not be ignored")
            error = rejected.structured_content["error"]
            self.assertEqual(error["code"], "INVALID_ARGUMENT")
            self.assertEqual(error["outcome"], "rejected")
            self.assertFalse(error["retry_safe"])
            accepted = await client.call_tool("character_status", {})
            self.assertFalse(accepted.is_error)
            self.assertFalse(accepted.structured_content["launches_application"])

    async def test_rejected_path_leaves_the_session_usable(self):
        async with stdio_client(parameters()) as (reader, writer), \
                ClientSession(reader, writer) as client:
            await client.initialize()
            names = {tool.name for tool in (await client.list_tools()).tools}
            self.assertEqual(names, TOOLS)
            rejected = await client.call_tool(
                "project_prepare_copy", {"source": "../input.chproj", "destination": "copy"})
            self.assertTrue(rejected.is_error)
            error = rejected.structured_content["error"]
            self.assertEqual(error["code"], "INVALID_ARGUMENT")
            self.assertEqual(error["outcome"], "rejected")
            self.assertEqual(error["operation"], "project_prepare_copy")
            self.assertFalse(error["retry_safe"])
            self.assertEqual(error["next_action"], "inspect_inputs")
            status = await client.call_tool("character_status", {})
            self.assertFalse(status.is_error)
            self.assertFalse(status.structured_content["launches_application"])


if __name__ == "__main__":
    unittest.main()

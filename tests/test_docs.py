import asyncio
import hashlib
import io
import json
import posixpath
import re
import tarfile
import tempfile
import unittest
from pathlib import Path

from cavi_mcp_core.contracts import UnknownToolError

from cavi_character_animator_mcp import server
from cavi_character_animator_mcp.bridge import CharacterRejected
from scripts.docs.build import build_documentation
from scripts.docs.lib import (
    DOCUMENTED_VERSION,
    PRODUCT_ID,
    REPO_ROOT,
    SOURCE_REL,
    list_files_recursive,
    navigation_paths,
)
from scripts.docs.release_artifact import create_product_docs_release_artifact
from scripts.docs.verify import verify_documentation

IDENTITY = {
    "version": DOCUMENTED_VERSION,
    "tag": f"v{DOCUMENTED_VERSION}",
    "commit": "0123456789abcdef0123456789abcdef01234567",
    "source_date_epoch": 1700000000,
}
ROOT = Path(REPO_ROOT)
PAGES = ROOT / SOURCE_REL / "pages"
REPOSITORY = "cavi-ai/character-animator-mcp"
ACCESS = ("read-only", "write", "destructive")


def digest(root, exclude_manifest=False):
    hash_value = hashlib.sha256()
    for relative in list_files_recursive(root):
        if exclude_manifest and relative == "manifest.json":
            continue
        hash_value.update(relative.encode())
        hash_value.update(b"\0")
        hash_value.update((Path(root) / relative).read_bytes())
        hash_value.update(b"\0")
    return hash_value.hexdigest()


def cells(line):
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def table_rows(lines):
    """The data rows of the first Markdown table in ``lines``, as lists of cells."""
    rows, in_table = [], False
    for line in lines:
        if line.startswith("|"):
            in_table = True
            row = cells(line)
            if not set("".join(row)) <= set("-: "):
                rows.append(row)
        elif in_table:
            break
    return rows[1:]


def name_of(cell):
    return cell.replace("`", "")


def names(cell):
    return [name_of(item.strip()) for item in cell.split(",") if item.strip()]


def registered_tools():
    return {tool.name: tool for tool in asyncio.run(server.mcp.list_tools())}


def access_of(tool):
    if tool.annotations.read_only_hint:
        return "read-only"
    return "destructive" if tool.annotations.destructive_hint else "write"


def readme_tools():
    lines = (ROOT / "README.md").read_text().splitlines()
    start = lines.index("| Tool | Purpose |")
    return [name_of(row[0]) for row in table_rows(lines[start:])]


def documented_tools():
    """Every row of the tool reference: name to (access, parameters, required, result fields)."""
    documented = {}
    for line in (PAGES / "reference/tools.md").read_text().splitlines():
        if not line.startswith("|"):
            continue
        row = cells(line)
        if len(row) == 5 and row[1] in ACCESS:
            parameters = names(row[2])
            documented[name_of(row[0])] = (
                row[1],
                {item.rstrip("*") for item in parameters},
                {item.rstrip("*") for item in parameters if item.endswith("*")},
                set(names(row[3])),
            )
    return documented


def documented_codes():
    lines = (PAGES / "reference/results-and-errors.md").read_text().splitlines()
    start = lines.index("### Codes")
    return {tuple(name_of(cell) for cell in row[:3]) for row in table_rows(lines[start:])}


def reported_codes():
    """The (code, outcome, next_action) a client receives for each documented cause."""
    server_codes = (
        "PLATFORM_UNSUPPORTED", "APP_UNAVAILABLE", "APP_IDENTITY_MISMATCH",
        "NATIVE_HELPER_UNAVAILABLE", "NATIVE_HELPER_BUILD_FAILED", "NATIVE_HELPER_UNSAFE",
        "STALE_STATE",
    )
    causes = [UnknownToolError("absent"), ValueError("bad"), FileNotFoundError("gone"),
              RuntimeError("busy"), *(CharacterRejected("refused", code) for code in server_codes)]
    errors = [server.mcp.failure("tool", cause).structured_content["error"] for cause in causes]
    return {(error["code"], error["outcome"], error["next_action"]) for error in errors}


class DocumentationTests(unittest.TestCase):
    def test_build_is_complete_stamped_and_reproducible(self):
        with tempfile.TemporaryDirectory() as temp:
            first, second = Path(temp) / "first", Path(temp) / "second"
            build_documentation({**IDENTITY, "output_root": first})
            build_documentation({**IDENTITY, "output_root": second})
            self.assertEqual(digest(first), digest(second))
            manifest = json.loads((first / "manifest.json").read_text())
            self.assertEqual(
                manifest,
                {
                    "schemaVersion": 2,
                    "package": PRODUCT_ID,
                    "product": PRODUCT_ID,
                    "version": DOCUMENTED_VERSION,
                    "contentSha256": digest(first, True),
                    "publicBasePath": f"/docs/{PRODUCT_ID}/v{DOCUMENTED_VERSION}",
                    "stableAlias": f"/docs/{PRODUCT_ID}",
                    "release": {"tag": IDENTITY["tag"], "commit": IDENTITY["commit"]},
                    "generatedAt": "2023-11-14T22:13:20.000Z",
                },
            )
            for relative in list_files_recursive(first):
                self.assertNotRegex((first / relative).read_text(), r"\{\{[A-Z][A-Z0-9_]*\}\}")
            stamped = (first / "release/version-and-support.md").read_text()
            self.assertIn(IDENTITY["commit"], stamped)
            self.assertIn(IDENTITY["tag"], stamped)
            verify_documentation({**IDENTITY, "output_root": first})

    def test_build_rejects_mismatched_versions_and_dirty_output(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "release version must be"):
                build_documentation(
                    {**IDENTITY, "version": "0.0.900", "output_root": Path(temp) / "bad"}
                )
            output = Path(temp) / "built"
            build_documentation({**IDENTITY, "output_root": output})
            original = (output / "navigation.json").read_bytes()
            (output / "navigation.json").write_text("stale\n")
            build_documentation({**IDENTITY, "output_root": output})
            self.assertEqual((output / "navigation.json").read_bytes(), original)
            (output / "stray.md").write_text("stray\n")
            with self.assertRaisesRegex(ValueError, "dirty output"):
                build_documentation({**IDENTITY, "output_root": output})

    def test_rebuild_for_new_commit_refreshes_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "built"
            build_documentation({**IDENTITY, "output_root": output})
            build_documentation({**IDENTITY, "commit": "f" * 40, "output_root": output})
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertEqual(manifest["release"]["commit"], "f" * 40)
            verify_documentation({**IDENTITY, "commit": "f" * 40, "output_root": output})

    def test_navigation_lists_every_page_once(self):
        navigation = json.loads((ROOT / SOURCE_REL / "navigation.json").read_text())
        self.assertEqual(sorted(navigation_paths(navigation)), sorted(list_files_recursive(PAGES)))

    def test_relative_page_links_resolve(self):
        pages = list_files_recursive(PAGES)
        broken = []
        for page in pages:
            text = (PAGES / page).read_text()
            for target in re.findall(r"\]\(([^)#\s]+\.md)(?:#[^)]*)?\)", text):
                if re.match(r"^[a-z]+:", target):
                    continue
                resolved = posixpath.normpath(posixpath.join(posixpath.dirname(page), target))
                if resolved not in pages:
                    broken.append(f"{page} -> {target}")
        self.assertEqual(broken, [])

    def test_page_links_stay_in_the_docs_or_on_github(self):
        outside = []
        for page in list_files_recursive(PAGES):
            for target in re.findall(r"\]\(([^)\s]+)\)", (PAGES / page).read_text()):
                if re.match(r"^[a-z]+:", target) and not target.startswith("https://github.com/cavi-ai/"):
                    outside.append(f"{page} -> {target}")
        self.assertEqual(outside, [])

    def test_documentation_names_no_private_paths(self):
        texts = {"README.md": (ROOT / "README.md").read_text()}
        texts.update({page: (PAGES / page).read_text() for page in list_files_recursive(PAGES)})
        found = [page for page, text in texts.items() if re.search(r"/Volumes/|/Users/", text)]
        self.assertEqual(found, [])

    def test_readme_links_resolve(self):
        readme = (ROOT / "README.md").read_text()
        broken = []
        for target in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", readme):
            if re.match(r"^[a-z]+:", target):
                continue
            if not (ROOT / target).exists():
                broken.append(target)
        self.assertEqual(broken, [])

    def test_readme_lists_exactly_the_registered_tools(self):
        self.assertEqual(sorted(readme_tools()), sorted(registered_tools()))

    def test_tool_reference_matches_the_registered_tools(self):
        documented = documented_tools()
        registered = registered_tools()
        self.assertEqual(sorted(documented), sorted(registered))
        for tool_name, tool in registered.items():
            access, parameters, required, results = documented[tool_name]
            schema = tool.input_schema
            self.assertEqual(access, access_of(tool), tool_name)
            self.assertEqual(parameters, set(schema["properties"]), tool_name)
            self.assertEqual(required, set(schema.get("required", [])), tool_name)
            self.assertEqual(results, set(tool.output_schema["properties"]), tool_name)

    def test_error_codes_match_what_a_client_receives(self):
        self.assertEqual(documented_codes(), reported_codes())

    def test_release_artifact_is_deterministic(self):
        with tempfile.TemporaryDirectory() as temp:
            docs = Path(temp) / "docs"
            build_documentation({**IDENTITY, "output_root": docs})
            results = [
                create_product_docs_release_artifact(
                    {**IDENTITY, "docs_root": docs, "output_directory": Path(temp) / name,
                     "repository": REPOSITORY}
                )
                for name in ("one", "two")
            ]
            first = results[0]["artifact_path"].read_bytes()
            self.assertEqual(first, results[1]["artifact_path"].read_bytes())
            sha = hashlib.sha256(first).hexdigest()
            asset = f"{PRODUCT_ID}-docs-{IDENTITY['tag']}.tar.gz"
            self.assertEqual(
                results[0]["envelope"],
                {
                    "schemaVersion": 1,
                    "slug": PRODUCT_ID,
                    "kind": "product-docs",
                    "version": DOCUMENTED_VERSION,
                    "tag": IDENTITY["tag"],
                    "repository": REPOSITORY,
                    "commit": IDENTITY["commit"],
                    "artifact": {
                        "url": f"https://github.com/{REPOSITORY}/releases/download/{IDENTITY['tag']}/{asset}",
                        "sha256": sha,
                        "format": "tar.gz",
                    },
                },
            )
            self.assertEqual(results[0]["checksum_path"].read_text(), f"{sha}  {asset}\n")
            with tarfile.open(fileobj=io.BytesIO(first), mode="r:gz") as archive:
                archived = archive.getnames()
            self.assertIn("cavi-release.json", archived)
            root = f"docs/{PRODUCT_ID}/v{DOCUMENTED_VERSION}/"
            self.assertTrue(all(item == "cavi-release.json" or item.startswith(root)
                                for item in archived))

    def test_artifact_rejects_docs_built_for_another_commit(self):
        with tempfile.TemporaryDirectory() as temp:
            docs = Path(temp) / "docs"
            build_documentation({**IDENTITY, "output_root": docs})
            with self.assertRaisesRegex(ValueError, "manifest is inconsistent"):
                create_product_docs_release_artifact(
                    {
                        **IDENTITY,
                        "commit": "a" * 40,
                        "docs_root": docs,
                        "output_directory": Path(temp) / "release",
                        "repository": REPOSITORY,
                    }
                )


if __name__ == "__main__":
    unittest.main()

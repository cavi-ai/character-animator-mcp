"""Drive the real server over stdio against Character Animator: the README first take."""

import asyncio
import json
import os
import shutil
import sys
import time
import wave
from pathlib import Path

from cavi_mcp_core.files import digest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = Path(__file__).resolve().parent
WORKSPACE = Path(sys.argv[1]).resolve()
PROJECT = sys.argv[2]
OUT = WORKSPACE / "first-take"


class Failed(Exception):
    """A tool call returned an error."""


def relative(path):
    return str(path.relative_to(WORKSPACE))


def recipe(export):
    """Every fifth exported PNG of the line's first 80 frames at 24/5 fps, the WAV clipped to those frames and
    the files the take came from. The media receipt holds at most 32 million PNG pixels: 16 frames of 1702 by 988.
    """
    frames = sorted((export / "Pip").glob("Pip.*.png"), key=lambda path: int(path.suffixes[0][1:]))[0:80:5]
    audio = export / "Pip" / "Pip.wav"
    with wave.open(str(audio), "rb") as stream:
        samples = len(frames) * 5 * stream.getframerate() // 24
    project = next((OUT / "Pip").glob("*.chproj"))
    roles = [("project", project), ("puppet", OUT / "media" / "Pip.psd"),
             ("dialogue_source", OUT / "media" / "dialogue.wav"), ("export_xml", export / "Pip.xml"),
             ("export_receipt", export / "Pip" / "Pip.json")]
    return {"schema": "cavi.character-export.v1", "version": 1, "name": "Pip", "loop": False, "alpha": "straight",
            "frame_rate": {"numerator": 24, "denominator": 5},
            "frames": [{"name": f"F{index:03d}", "path": relative(path), "sha256": digest(path)}
                       for index, path in enumerate(frames)],
            "audio": {"path": relative(audio), "sha256": digest(audio), "start": 0, "clip_in_samples": 0,
                      "duration_samples": samples},
            "source_roles": [{"role": role, "path": relative(path), "sha256": digest(path)} for role, path in roles]}


async def main():
    OUT.mkdir()
    shutil.copytree(HERE / "media", OUT / "media")
    env = {**os.environ, "CAVI_ADOBE_WORKSPACE": str(WORKSPACE)}
    params = StdioServerParameters(command=sys.executable, args=["-m", "cavi_character_animator_mcp.server"], env=env)
    async with stdio_client(params) as (r, w), ClientSession(r, w, read_timeout_seconds=900) as client:
        await client.initialize()

        async def call(tool, **arguments):
            reply = await client.call_tool(tool, arguments)
            body = reply.structured_content if not reply.is_error else reply.content[0].text
            if reply.is_error:
                raise Failed(f"{tool}: {body}")
            print(tool, json.dumps({key: body[key] for key in ("status", "state", "completion", "prepared_copy_id",
                                                               "lease_id", "operation_id") if key in body}),
                  flush=True)
            return body

        async def until(check, seconds, pause=2):
            """The fingerprint once two observations in a row pass the check and match."""
            deadline, previous = time.monotonic() + seconds, None
            while time.monotonic() < deadline:
                state = (await client.call_tool("inspect", {})).structured_content
                current = state["native"]["state"]["fingerprint"] if check(state) else None
                if current is not None and current == previous:
                    return current
                previous = current
                await asyncio.sleep(pause)
            raise Failed("Character Animator did not reach the expected state")

        def import_finished(state):
            """The chooser is closed and File > Import is enabled again."""
            native = state["native"]["state"]
            return (not any(window.get("modal") for window in native["windows"])
                    and (native.get("focused_window") or {}).get("identifier") not in ("open-panel", "GoToWindow")
                    and native["menu_commands"]["import"]["enabled"])

        async def fingerprint():
            return (await call("inspect"))["native"]["state"]["fingerprint"]

        await call("character_status")
        copy = await call("project_prepare_copy", source=PROJECT, destination="first-take/Pip")
        await call("project_open_prepared_copy", prepared_copy_id=copy["prepared_copy_id"])
        root = str(OUT / "Pip")
        await until(lambda state: state["native"]["state"].get("project_roots") == [root], 120)
        project = await call("inspect")
        lease = (await call("session_control", action="claim", owner="first-take",
                            expected_project=project["project_id"],
                            prepared_copy_id=copy["prepared_copy_id"]))["lease_id"]
        await call("import_media", source="first-take/media/Pip.psd", kind="puppet_psd", lease_id=lease)
        await until(import_finished, 60)
        await call("import_media", source="first-take/media/dialogue.wav", kind="audio_wav", lease_id=lease)
        await until(import_finished, 60)
        await asyncio.sleep(3)
        await call("project_select", name="Pip", item_type="puppet", extend=False,
                   expected_fingerprint=await fingerprint(), lease_id=lease)
        await call("project_select", name="dialogue.wav", item_type="audio", extend=True,
                   expected_fingerprint=await fingerprint(), lease_id=lease)
        await call("scene_action", action="add_to_new_scene", expected_fingerprint=await fingerprint(),
                   lease_id=lease)
        ready = await until(lambda state: state["native"]["state"]["menu_commands"]
                            ["create_take_from_scene_audio"]["enabled"], 60)
        await call("scene_action", action="create_take_from_scene_audio", expected_fingerprint=ready, lease_id=lease)
        ready = await until(lambda state: state["native"]["state"]["menu_commands"]["export_png_wav"]["enabled"]
                            and import_finished(state), 120)
        await call("scene_export", directory="first-take/export", name="Pip", expected_fingerprint=ready,
                   lease_id=lease)
        export = OUT / "export"
        deadline = time.monotonic() + 300
        while not (export / "Pip" / "Pip.json").exists() or not (export / "Pip.xml").exists():
            if time.monotonic() > deadline:
                raise Failed("The export did not finish in 300 seconds")
            await asyncio.sleep(2)
        (export / "recipe.json").write_text(json.dumps(recipe(export), indent=1))
        inspected = await call("export_inspect", recipe="first-take/export/recipe.json")
        ingested = await call("export_ingest", recipe="first-take/export/recipe.json", directory="first-take/handoff")
        await call("session_control", action="release", lease_id=lease)
        print(json.dumps({"frame_count": inspected["frame_count"], "fps": inspected["fps"],
                          "duration": inspected["duration"], "audio": inspected["audio"],
                          "handoff": ingested["handoff"], "media_receipt": ingested["media_receipt"]}, indent=1))


try:
    asyncio.run(main())
except* Failed as group:
    error = group
    while isinstance(error, BaseExceptionGroup):
        error = error.exceptions[0]
    sys.exit(str(error))

"""Typed Character Animator MCP with cooperative ownership and native evidence."""

import json
import threading
from typing import Annotated, Any, Literal

import anyio.to_thread
from cavi_mcp_core.contracts import Result, failure
from cavi_mcp_core.media import png_content
from cavi_mcp_core.server import DESTRUCTIVE as MUTATE
from cavi_mcp_core.server import READ_ONLY as READ
from cavi_mcp_core.server import WRITES as WRITE
from cavi_mcp_core.server import Server
from mcp.server.mcpserver import AcceptedElicitation, Context, Elicit, ElicitationResult, Resolve
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import CallToolResult, TextContent
from pydantic import BaseModel, Field, StrictBool, StrictInt

from . import media
from .animator import CharacterAnimator
from .bridge import CharacterRejected, CharacterUnknown, NativeBridge
from .config import data_dir, workspace


class CharacterAnimatorServer(Server):
    def failure(self, name, error):
        """An unknown outcome points at inspect, which reads the app and unresolved operation state."""
        return failure(name, error, unknown_next_action="inspect")


mcp = CharacterAnimatorServer("cavi-character-animator-mcp", package="cavi-character-animator-mcp",
                              anticipated=(), instructions=(
    "Controls the installed macOS Character Animator through a bounded native adapter. "
    "Start with character_status and inspect. Claim session_control using the observed project_id. "
    "Save a new owned project copy before scene mutations. Native menus, visual observations and "
    "verified exported files are different evidence; never treat a dispatched command as completion. "
    "Inspect unresolved operation journals instead of automatically retrying. Server startup never "
    "launches the app, requests permissions, records a camera/microphone or signs into an account."
))


class CharacterStatus(Result):
    available: bool
    connected: bool
    native: dict[str, Any] | None
    reason: str | None
    launches_application: Literal[False]


class CharacterInspection(Result):
    project_id: str
    native: dict[str, Any]
    pending_operation: dict[str, Any] | None
    project_items: list[dict[str, str]] | None = None
    project_items_error: str | None = None
    timeline_selection: bool | None = None
    launches_application: Literal[False]


class CharacterOwnership(Result):
    project_id: str
    lease_id: str | None = None
    owner: str | None
    expires_at: float | None
    state: Literal["owned", "unclaimed"]
    pending_operation: dict[str, Any] | None
    prepared_copy_id: str | None = None
    owned_root: str | None = None


class CharacterPreparedCopy(Result):
    status: Literal["prepared_copy"]
    prepared_copy_id: str
    source: str
    destination: str
    source_identity: dict[str, int]
    destination_identity: dict[str, int]
    files: list[dict[str, Any]]
    launches_application: Literal[False]


class CharacterPreparedOpen(Result):
    status: Literal["prepared_copy_opened", "prepared_copy_open_requested"]
    completion: Literal["observed", "unverified"]
    prepared_copy_id: str
    operation_id: str
    project_id: str | None
    native: dict[str, Any]
    retry_safe: Literal[False]
    launches_application: Literal[True]


class CharacterCapture(Result):
    path: str
    sha256: str
    native: dict[str, Any]
    identity: Literal["observed_window_and_ocr"]
    launches_application: Literal[False]


class CharacterProject(Result):
    status: Literal["owned_copy"]
    operation_id: str
    project_id: str
    project_root: str
    project_file: str
    files: list[dict[str, Any]]
    source_identity: Literal["observed_native_project_root"]
    retry_safe: Literal[False]


class CharacterImportedMedia(Result):
    operation_id: str
    status: Literal["native_import_submitted"]
    completion: Literal["observed", "unverified"]
    kind: Literal["puppet_psd", "audio_wav"]
    source: dict[str, Any]
    import_copy: dict[str, Any]
    project_item: dict[str, str] | None = None
    native: dict[str, Any]
    source_identity: Literal["hashed_private_import_copy"]
    retry_safe: Literal[False]


class CharacterSceneAction(Result):
    operation_id: str
    status: Literal["native_scene_action_submitted"]
    action: Literal["add_to_new_scene", "create_take_from_scene_audio", "compute_lip_sync",
                    "set_work_area_to_selection", "export_png_wav"]
    completion: Literal["observed", "unverified"]
    expected_state_fingerprint: str
    project_item: dict[str, str] | None = None
    native_dispatch: dict[str, Any]
    native_after: dict[str, Any]
    selection_identity: Literal["caller_observed_state_fingerprint"]
    retry_safe: Literal[False]


class CharacterProjectSelection(Result):
    operation_id: str
    status: Literal["native_project_item_selected"]
    name: str
    item_type: Literal["puppet", "audio", "scene"]
    extend: bool
    expected_state_fingerprint: str
    selection_evidence: dict[str, Any]
    native: dict[str, Any]
    completion: Literal["unverified"]
    retry_safe: Literal[False]


class CharacterOperation(Result):
    operation_id: str
    status: str
    native: dict[str, Any]
    retry_safe: Literal[False]


class CharacterMediaInspection(Result):
    schema_: Literal["cavi.character-export.v1"] = Field(alias="schema")
    version: Literal[1]
    status: Literal["inspected"]
    name: str
    fps: dict[str, int]
    frame_count: int
    duration: float
    frame_order_source: Literal["explicit_recipe"]
    frame_rate_source: Literal["caller_declared"]
    native_export: Literal["not_verified"]
    launches_applications: Literal[False]


class CharacterHandoff(Result):
    schema_: Literal["cavi.character-handoff.v1"] = Field(alias="schema")
    version: Literal[1]
    status: Literal["ingested"]
    name: str
    media_receipt: dict[str, str]
    cutscene_audio: dict[str, Any] | None
    handoff: dict[str, str]
    native_export: Literal["not_verified"]
    launches_applications: Literal[False]


# Long side of the image capture returns; a larger window capture is scaled down.
CAPTURE_EDGE = 1568


class ImportCancellation(BaseModel):
    cancelled: StrictBool = Field(description="True if you cancelled this import in Character Animator.")


def client():
    return CharacterAnimator(workspace(), data_dir() / "character-animator")


def ask_import_cancellation(action: str, operation_id: str, ctx: Context):
    """For confirm_cancelled_import on a pending import, ask the user when the client supports forms."""
    capabilities = ctx.client_capabilities
    elicitation = capabilities.elicitation if capabilities is not None else None
    if (action != "confirm_cancelled_import" or elicitation is None
            or (elicitation.form is None and elicitation.url is not None)):
        return None
    try:
        pending = client().read("operation.json")
    except (CharacterUnknown, OSError, ValueError):
        return None
    if (not isinstance(pending, dict) or pending.get("operation_id") != operation_id
            or pending.get("operation") != "import" or pending.get("state") != "unknown"):
        return None
    return Elicit(f"Did you cancel the Character Animator import for operation {operation_id}? "
                  "Answer yes only if you closed its Import chooser without importing.", ImportCancellation)


async def execute(function):
    cancelled = threading.Event()
    try:
        return await anyio.to_thread.run_sync(lambda: function(cancelled), abandon_on_cancel=True)
    except (CharacterRejected, CharacterUnknown, OSError, ValueError) as exc:
        raise ToolError(str(exc)) from exc
    except BaseException:
        cancelled.set()
        raise


@mcp.tool(annotations=READ)
async def character_status() -> CharacterStatus:
    """Inspect app/control availability without launch, recording or permission prompts."""
    def run(cancelled):
        try:
            native = NativeBridge(data_dir() / "character-animator").call("status", cancelled=cancelled)
        except CharacterRejected as exc:
            return {"available": False, "connected": False, "native": None, "reason": str(exc),
                    "launches_application": False}
        state = native["state"]
        connected = type(state.get("pid")) is int and state["pid"] > 0 and state.get("accessibility_trusted") is True
        return {"available": True, "connected": connected, "native": native,
                "reason": None if connected else "Start the app and inspect local control permissions",
                "launches_application": False}
    return await execute(run)


@mcp.tool(annotations=READ)
async def inspect() -> CharacterInspection:
    """Observe actual process, project-root evidence, native controls and unresolved operation state.

    project_items lists the visible Project panel rows (name; puppet, audio or scene) read from the window;
    it needs Screen Recording access, and project_items_error says why it is missing. timeline_selection
    is whether Timeline > Set Work Area to Selection is enabled, which needs selected timeline tracks.
    """
    return await execute(lambda cancelled: client().inspect(cancelled, items=True))


@mcp.tool(annotations=WRITE)
async def capture(directory: str) -> Annotated[CallToolResult, CharacterCapture]:
    """Capture only the Character Animator window with bounded OCR into a new workspace directory.

    The PNG also comes back as image content, at most 1568 px on its long side.
    Observed text/geometry are visual evidence, not native scene IDs. Never starts recording.
    """
    def run(cancelled):
        data = client().capture(directory, cancelled)
        return data, png_content(data["path"], CAPTURE_EDGE)

    data, image = await execute(run)
    structured = CharacterCapture.model_validate(data).model_dump(mode="json", by_alias=True)
    return CallToolResult(content=[TextContent(type="text", text=json.dumps(structured)), image],
                          structured_content=structured)


@mcp.tool(annotations=WRITE)
async def session_control(action: Literal["inspect", "claim", "renew", "release", "resume"],
                          owner: str | None = None, expected_project: str | None = None,
                          lease_id: str | None = None,
                          ttl_seconds: Annotated[StrictInt, Field(ge=30, le=3600)] = 600,
                          pending_operation_id: str | None = None,
                          prepared_copy_id: str | None = None) -> CharacterOwnership:
    """Claim, renew, release, or resume a matching expired lease for one unknown operation.

    Resume requires the expired lease ID, same owner, project ID and exact unknown operation ID. It renews
    ownership after process/root checks and dispatches no native command or chooser action. Claiming a
    prepared copy requires its private ID and a fresh observation of that exact native root.
    """
    return await execute(lambda cancelled: client().session(action, owner, expected_project,
                                                           lease_id, ttl_seconds, cancelled,
                                                           pending_operation_id, prepared_copy_id))


@mcp.tool(annotations=WRITE)
async def project_prepare_copy(source: str, destination: str) -> CharacterPreparedCopy:
    """Copy a closed saved workspace .chproj tree and verify its file hashes before native opening.

    The source must not be open in Character Animator. This creates only a new workspace copy;
    pass its prepared_copy_id to project_open_prepared_copy, inspect the opened root,
    then claim it with session_control and the same prepared_copy_id.
    """
    return await execute(lambda cancelled: client().prepare_copy(source, destination, cancelled))


@mcp.tool(annotations=WRITE)
async def project_open_prepared_copy(prepared_copy_id: str) -> CharacterPreparedOpen:
    """Open only the exact closed-project copy previously prepared by project_prepare_copy.

    Inspect the opened native root, then claim it with session_control and the same prepared_copy_id.
    """
    return await execute(lambda cancelled: client().session(
        "open_prepared_copy", cancelled=cancelled, prepared_copy_id=prepared_copy_id))


@mcp.tool(annotations=MUTATE)
async def project_save_copy(directory: str, name: str, lease_id: str) -> CharacterProject:
    """Native Save Project As into a new workspace project, then verify actual root and project files.

    directory is an existing parent; name is a safe ASCII project name. Does not edit the source
    scene or discard unsaved state. A missing original file hash remains explicitly unavailable.
    """
    return await execute(lambda cancelled: client().save_copy(directory, name, lease_id, cancelled))


@mcp.tool(annotations=MUTATE)
async def import_media(source: str, kind: Literal["puppet_psd", "audio_wav"],
                       lease_id: str) -> CharacterImportedMedia:
    """Import a hash-pinned workspace PSD puppet or WAV into the owned project.

    PSDs use the native Import chooser. WAVs are handed to the already-running app. It waits for the app to
    finish; completion is observed with project_item when a new puppet or audio row appears in the Project panel.
    The first WAV after a project opens is unverified: its row is drawn only once the Project panel is clicked.
    """
    return await execute(lambda cancelled: client().import_media(source, kind, lease_id, cancelled))


@mcp.tool(annotations=MUTATE)
async def scene_action(action: Literal["add_to_new_scene", "create_take_from_scene_audio",
                                      "compute_lip_sync", "set_work_area_to_selection", "export_png_wav"],
                       expected_fingerprint: str, lease_id: str) -> CharacterSceneAction:
    """Run one fixed menu action on the current owned-project selection and wait for the app to finish.

    add_to_new_scene is observed with project_item when a new scene row appears. set_work_area_to_selection
    spans the work area over the selected timeline tracks or take bars; while the work area is enabled,
    scene_export exports only that range. Copy the fingerprint from the latest inspect.
    """
    return await execute(lambda cancelled: client().scene_action(action, expected_fingerprint,
                                                                   lease_id, cancelled))


@mcp.tool(annotations=MUTATE)
async def scene_export(directory: str, name: str, expected_fingerprint: str,
                       lease_id: str) -> CharacterOperation:
    """Export PNG Sequence and WAV for the current owned scene into a new workspace directory.

    It waits for the frames, WAV and sidecars; completion is observed with frame_count, frames, wav, json
    and xml once they exist and stop changing. Validate them with export_inspect.
    """
    return await execute(lambda cancelled: client().scene_export(
        directory, name, expected_fingerprint, lease_id, cancelled))


@mcp.tool(annotations=MUTATE)
async def project_select(name: str, item_type: Literal["puppet", "audio", "scene"],
                         extend: StrictBool, expected_fingerprint: str,
                         lease_id: str) -> CharacterProjectSelection:
    """Select one uniquely OCR-matched Project-panel row by name and type.

    extend controls additive selection; use the latest inspect fingerprint. OCR evidence is not a scene ID.
    """
    return await execute(lambda cancelled: client().project_select(
        name, item_type, extend, expected_fingerprint, lease_id, cancelled))


@mcp.tool(annotations=WRITE)
async def operation_control(action: Literal["inspect", "verify_copy", "continue_copy", "continue_import", "continue_export",
                                            "confirm_cancelled_import", "reconcile_import", "cancel_unsubmitted",
                                            "reconcile_unsubmitted_copy", "reconcile_copy_after_exit",
                                            "abandon_after_exit"],
                            operation_id: str,
                            answer: Annotated[ElicitationResult[ImportCancellation],
                                              Resolve(ask_import_cancellation)],
                            lease_id: str | None = None,
                            user_confirmed_cancelled: StrictBool = False) -> CharacterOperation:
    """Inspect or continue exact pending copy/import/export operations, verify a copy, or reconcile cancellation.

    continue_export resumes only the journaled Export Scene/Go To chooser and output directory.
    continue_import never replays File > Import and requires the existing chooser, except for the single
    recorded pre-menu focus rejection. confirm_cancelled_import asks the user when the client supports
    elicitation; otherwise it requires user_confirmed_cancelled from the user's own report. It also needs
    matching process/root/source evidence; it issues no native command and is not native-verified cancellation.
    reconcile_import resolves an unknown import, with no chooser or modal open, when the Project panel shows a
    puppet or audio row that was not there before it; it issues no native command and leaves the app running.
    cancel_unsubmitted applies only to an observed unsubmitted Save As chooser.
    reconcile_unsubmitted_copy records only a closed, pre-submit initial Save As stage after stable source checks;
    it sends no native command and does not imply user cancellation.
    reconcile_copy_after_exit resolves only a submitted initial Save As after the exact app process has exited,
    no matching app instance is running, and the original destination remains absent; it verifies no copy.
    abandon_after_exit archives an unknown operation on a first-hand owned project only after two stable
    observations confirm the original app process and all Character Animator instances have exited. It
    preserves project files and records the native outcome as unknown.
    """
    confirmation = "caller_reported"
    if not isinstance(answer, AcceptedElicitation):
        user_confirmed_cancelled, confirmation = False, "elicited"
    elif isinstance(answer.data, ImportCancellation):
        user_confirmed_cancelled, confirmation = answer.data.cancelled, "elicited"
    return await execute(lambda cancelled: client().operation_control(
        action, operation_id, lease_id, cancelled, user_confirmed_cancelled, confirmation))


@mcp.tool(annotations=READ)
async def export_inspect(recipe: str) -> CharacterMediaInspection:
    """Validate explicitly ordered native-export PNG/WAV/source hashes and exact dialogue sample timing.

    Frame rate/order are caller declarations; proprietary project/puppet files are opaque provenance.
    This inspects existing files and does not perform a native Character Animator export.
    """
    return await execute(lambda _: media.inspect_export(workspace(), recipe))


@mcp.tool(annotations=WRITE)
async def export_ingest(recipe: str, directory: str) -> CharacterHandoff:
    """Create a pinned media receipt and measured PCM audio descriptor for Unity cutscene delivery.

    Outputs go into a new directory. Preserves editable project/performance/XML provenance;
    does not establish native rigging, lip-sync correctness, playback or visual acceptance.
    """
    return await execute(lambda _: media.ingest_export(workspace(), recipe, directory))


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

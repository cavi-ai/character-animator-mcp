# Overview

`cavi-character-animator-mcp` is an MCP server for Adobe Character Animator on macOS. It prepares closed project
copies, tracks which session owns the open project, reads the running application's state, imports puppets and
dialogue audio, submits scene exports and verifies the exported PNG and WAV files.

It runs on macOS with Character Animator installed and licensed by you. The server does not supply a license,
sign in or accept terms. Starting the server never launches the application, requests a permission, records a
camera or microphone or signs into an account.

## What it does

- Reads the application: `character_status` reports whether the application is running and reachable, and
  `inspect` returns the process, the open project root, the native controls and any unresolved operation.
  `capture` saves a PNG of the Character Animator window with recognized text.
- Takes ownership of a project: `project_prepare_copy` copies a closed `.chproj` tree into the workspace and
  verifies its file hashes, `project_open_prepared_copy` opens that copy, and `session_control` claims, renews,
  releases or resumes a lease on the open project. `project_save_copy` saves the owned project as a new copy.
- Changes the owned project: `import_media` submits a puppet PSD or a dialogue WAV, `project_select` selects a
  puppet, audio or scene row by name, and `scene_action` runs one fixed menu action on the selection.
- Exports: `scene_export` submits a PNG Sequence and WAV export of the owned scene into a new workspace directory.
- Recovers: `operation_control` inspects, verifies or continues a recorded native operation, and reconciles or
  archives one whose outcome is unknown.
- Checks the files: `export_inspect` validates exported PNG and WAV files against an explicit recipe, and
  `export_ingest` writes a pinned media receipt and a measured audio descriptor for them.

## How a call works

1. Every path is relative to one workspace directory, set by `CAVI_ADOBE_WORKSPACE`.
2. A tool that changes the application records the operation in a private journal before it dispatches a native
   command, then drives Character Animator through a native helper built from the packaged Swift source.
3. The result says what was observed. A native menu or chooser that was dispatched is reported as submitted with
   `completion` `unverified`: it is not treated as done until the application and the output files show it.

`session_control`, `project_prepare_copy`, `project_open_prepared_copy`, `operation_control` and the tools that
change the project (`project_save_copy`, `import_media`, `scene_action`, `scene_export`, `project_select`) take one
session lock per workspace. A second such request waits up to 15 seconds, then is refused.

## What it refuses

A mutation is refused when the lease is missing, expired or belongs to another project, when an earlier operation
is unresolved, when the `expected_fingerprint` is not the application's current state fingerprint, or when the
project is not an owned copy. Nothing is retried by the server: every result carries `retry_safe` `false` where it
reports an operation. See [Project copies and ownership](../guides/project-copies.md) and
[Recovery and unknown outcomes](../guides/recovery.md).

## Where to go next

- [Setup](../guides/setup.md), then [Your first result](../guides/first-result.md).
- The [tool reference](../reference/tools.md) lists every tool with its parameters and results.
- [Version and support](../release/version-and-support.md) says what the documentation covers.

# Changelog

Versions come from git tags; a pull request adds its lines under Unreleased and never edits a version.

## Unreleased

### Added

- `capture` returns the window PNG as image content, at most 1568 px on its long side, beside its receipt.
- `operation_control` `confirm_cancelled_import` asks the user through MCP elicitation when the client supports it;
  its result and receipt record `confirmation` as `elicited` or `caller_reported`.
- `examples/first-take` imports a puppet PSD and a spoken line, records a lip-sync take from the scene audio,
  exports it and ingests the frames and WAV into a pinned handoff.

### Changed

- `inspect` lists the visible Project panel rows as `project_items` and reports `timeline_selection`.
- `import_media` and `scene_action` `add_to_new_scene` wait for Character Animator and report `completion` `observed`
  with the new Project row as `project_item`.
- `scene_export` waits for the exported frames, WAV and sidecars and reports `completion` `observed` with
  `frame_count`, `frames`, `wav`, `json` and `xml`.
- `scene_action` adds `set_work_area_to_selection`.
- `operation_control` adds `reconcile_import`, which resolves an unknown import from its new Project row without
  quitting Character Animator.
- An unknown outcome's `next_action` is `inspect`.
- The native helper launches through `cavi_mcp_core.owned_exec`, so it registers with the process owner that
  `CAVI_MCP_PROCESS_OWNER` names.

### Fixed

- A rejected `project_prepare_copy` removes its temporary copy when the source has read-only folders, and reports
  an unknown outcome when the copy cannot be removed.
- `export_inspect` and `export_ingest` accept the 32-bit float WAV that the PNG Sequence and WAV export writes, and
  report the audio's `sample_format`.
- `import_media` completes when the Import chooser's location popup carries no URL; the selected file row's URL
  proves the chosen file.
- Chooser observation walks the focused window first and only the last three columns of the Import column browser,
  so a deep folder chain no longer truncates the tree before the selected file.
- A native chooser step waits for three observations before deciding a slow observation was stable.

## 0.1.0 - 2026-11-19

- The server moved here from `cavi-adobe-mcp`.
- Added the documentation tree, its build and verification, and a release documentation artifact.

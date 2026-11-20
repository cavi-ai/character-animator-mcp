# Changelog

Versions come from git tags; a pull request adds its lines under Unreleased and never edits a version.

## Unreleased

### Changed

- An unknown outcome's `next_action` is `inspect`.
- The native helper launches through `cavi_mcp_core.owned_exec`, so it registers with the process owner that
  `CAVI_MCP_PROCESS_OWNER` names.

### Fixed

- A rejected `project_prepare_copy` removes its temporary copy when the source has read-only folders, and reports
  an unknown outcome when the copy cannot be removed.

## 0.1.0 - 2026-11-19

- The server moved here from `cavi-adobe-mcp`.
- Added the documentation tree, its build and verification, and a release documentation artifact.

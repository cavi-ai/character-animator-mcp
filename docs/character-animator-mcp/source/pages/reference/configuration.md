# Configuration

The server is configured with environment variables, set in the `env` of its entry in the MCP client.

| Variable | Used by | Meaning |
|---|---|---|
| `CAVI_ADOBE_WORKSPACE` | every tool that takes a path, and the journals | Required. Absolute directory every tool path is relative to and must stay inside. |
| `CAVI_ADOBE_DATA` | every tool that reaches the native helper | Private server state: native helper builds and Character Animator journals. Default: `~/.local/share/cavi-adobe-mcp`. |
| `CAVI_CHARACTER_ANIMATOR_APP` | every tool that finds the application | Absolute path of the Character Animator `.app` to use. It must be Character Animator (bundle identifier `com.adobe.Character-Animator.application`); a wrong path is reported, never replaced by another install. Default: the newest installed version under `/Applications`. |

## The private data directory

Under `CAVI_ADOBE_DATA` the server creates `character-animator/`. The helper build folders, the attempt folder
and the per-workspace state folder are created owner-only (mode 0700). `<state>` below is the folder named by 16
hexadecimal characters of a hash of the workspace path, so each workspace has its own.

| Path in `character-animator/` | Holds |
|---|---|
| `native/<sha256 of the helper source>/` | The compiled helper, `build.json` (its receipt) and a build lock. |
| `character-native-attempts/` | A progress log for each chooser continuation; removed when the call succeeds. |
| `<state>/lease.json` | The current lease: owner, project, expiry and owned root. |
| `<state>/operation.json` | The unresolved operation, if any. |
| `<state>/operations/<operation_id>.json` | The record of each resolved operation. |
| `<state>/prepared-copies/<prepared_copy_id>.json` | The receipt of a prepared copy. |
| `<state>/inputs/<id>/` | The read-only copy of each imported file. |
| `<state>/session.lock` | The lock that serializes requests. |

Keep these records private: they hold project paths and file hashes. Removing `operation.json` by hand discards the
record of an unknown outcome.

## Fixed limits

| Limit | Value |
|---|---|
| Session lock wait | 15 seconds |
| Native request | 45 seconds, and a 4 MiB response |
| Helper compile | 300 seconds |
| Lease lifetime (`ttl_seconds`) | 30 to 3600 seconds, default 600 |
| Project tree for a copy | 8192 entries; 4096 files and 1 GiB for the file receipt |
| Import source (`import_media`) | at most 1 GiB, not empty |
| Capture image | at most 32 MiB |
| Project item name (`project_select`) | 1 to 128 characters |
| Owner name (`session_control`) | 1 to 128 characters |
| Export recipe | at most 4 MiB; 1 to 1000 frames; 62 source roles; 300 seconds |
| Dialogue WAV | at most 64 MiB, 300 seconds, 8 to 192 kHz, mono or stereo |

## Dependencies

The server depends on `cavi-mcp-core` (application lookup, bounded subprocesses, the server type, file and
workspace rules, the media receipt `export_ingest` writes and the operation journal helpers) by version range.

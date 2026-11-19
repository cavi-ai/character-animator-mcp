# Cavi Character Animator MCP

## Work on a copy you own.

MCP server for Adobe Character Animator on macOS. It prepares closed project copies, tracks which session owns an
open project, reads the running application's state, imports puppets and dialogue audio, exports scenes and
verifies the exported PNG and WAV files.

The server drives the application you have installed and signed in to, through a native helper. Every dispatched
command is reported as unverified until the application and the output files show it. Bring your own licensed
application.

## Install

Requires macOS, Adobe Character Animator installed and signed in, the Swift command-line compiler
(`xcode-select --install`; the server compiles its native helper on first use) and Python 3.15 or later with
[uv](https://docs.astral.sh/uv/). The MCP host needs Accessibility access; `capture` also needs Screen Recording
access. You supply your own licensed Adobe applications.

```sh
uv tool install cavi-character-animator-mcp
```

Upgrade with `uv tool upgrade cavi-character-animator-mcp`. To work from a checkout instead, see
[CONTRIBUTING.md](CONTRIBUTING.md).

## Quickstart

Register the stdio server with your MCP client and set the workspace:

```json
{
  "mcpServers": {
    "character-animator": {
      "command": "cavi-character-animator-mcp",
      "env": {"CAVI_ADOBE_WORKSPACE": "/absolute/path/to/workspace"}
    }
  }
}
```

If your client does not inherit your shell's `PATH`, use the absolute path that
`command -v cavi-character-animator-mcp` prints. Then try a request like:

> Check that Character Animator is reachable, prepare a copy of `projects/Hero`, open it and claim it.

The [setup guide](docs/character-animator-mcp/source/pages/guides/setup.md) and
[first result](docs/character-animator-mcp/source/pages/guides/first-result.md) walk through the workflow. Tool
paths are relative to the workspace.

## What you can do

- Read the application: whether it is running and reachable, its process, project root, native controls and
  unresolved operation state, and a capture of its window.
- Copy a closed project into the workspace with its file hashes verified, open the copy and claim it with a lease
  before any change.
- Import a puppet PSD or dialogue WAV, select a puppet, audio or scene row by name and run one fixed menu action on
  the selection.
- Submit a PNG Sequence and WAV export of the owned scene into a new directory, then validate the exported files
  against an explicit recipe and write a pinned media receipt with a measured audio descriptor.
- Inspect, verify, continue or reconcile a recorded native operation, and keep unknown outcomes instead of
  retrying them.

| Tool | Purpose |
|---|---|
| `character_status` | Report whether the application is running and reachable. |
| `inspect` | Read the process, project root, native controls and unresolved operation state. |
| `capture` | Capture the Character Animator window with text recognition into a new workspace directory. |
| `session_control` | Inspect, claim, renew, release or resume ownership of an open project. |
| `project_prepare_copy` | Copy a closed `.chproj` tree into the workspace and verify its file hashes. |
| `project_open_prepared_copy` | Open a prepared copy in the application. |
| `project_save_copy` | Save an owned project as a new copy. |
| `import_media` | Import a puppet PSD or a dialogue WAV. |
| `scene_action` | Run one menu action on the selection: add to a new scene, create a take from scene audio, compute lip sync or export PNG and WAV. |
| `scene_export` | Submit a PNG Sequence and WAV export of the owned scene into a new workspace directory. |
| `project_select` | Select a puppet, audio or scene row in the Project panel by name. |
| `operation_control` | Inspect, verify or continue a recorded native operation. |
| `export_inspect` | Validate exported PNG and WAV files, their hashes and the dialogue sample timing. |
| `export_ingest` | Write a pinned media receipt and a measured audio descriptor for the exported files. |

See the [tool reference](docs/character-animator-mcp/source/pages/reference/tools.md) for parameters and results.

## Closed projects and recovery

For a closed Character Animator project, prepare a copy with `project_prepare_copy`, open that prepared copy, inspect
its project root and claim it with `session_control` before editing. A WAV handoff receipt does not confirm import:
check that the audio appears in the project's Audio rows. After a process exits, the operation control and session
control tools provide explicit reconciliation and lease release actions; they preserve unknown outcomes and project
files.

Keep workspace ownership records private. Each native operation is recorded before it runs. If an operation reports
an unknown outcome, inspect the application and outputs or reconcile the recorded operation before trying again. See
[project copies and ownership](docs/character-animator-mcp/source/pages/guides/project-copies.md) and
[recovery and unknown outcomes](docs/character-animator-mcp/source/pages/guides/recovery.md).

## Documentation

The documentation source is in `docs/character-animator-mcp/source`:

- [Overview](docs/character-animator-mcp/source/pages/introduction/overview.md) and
  [setup](docs/character-animator-mcp/source/pages/guides/setup.md)
- Guides: [your first result](docs/character-animator-mcp/source/pages/guides/first-result.md),
  [project copies and ownership](docs/character-animator-mcp/source/pages/guides/project-copies.md),
  [importing and exporting](docs/character-animator-mcp/source/pages/guides/importing-and-exporting.md),
  [recovery and unknown outcomes](docs/character-animator-mcp/source/pages/guides/recovery.md) and
  [troubleshooting](docs/character-animator-mcp/source/pages/guides/troubleshooting.md)
- Reference: [tools](docs/character-animator-mcp/source/pages/reference/tools.md),
  [results and errors](docs/character-animator-mcp/source/pages/reference/results-and-errors.md),
  [configuration](docs/character-animator-mcp/source/pages/reference/configuration.md) and
  [testing and evaluation](docs/character-animator-mcp/source/pages/reference/testing.md)
- [Security model](docs/character-animator-mcp/source/pages/security/model.md) and
  [version and support](docs/character-animator-mcp/source/pages/release/version-and-support.md)

## Configuration

| Variable | Meaning |
|---|---|
| `CAVI_ADOBE_WORKSPACE` | Absolute directory every tool path is relative to. Required. |
| `CAVI_ADOBE_DATA` | Private server state: native helper builds and Character Animator journals. Defaults to `~/.local/share/cavi-adobe-mcp`. |
| `CAVI_CHARACTER_ANIMATOR_APP` | The Character Animator `.app` to use. |

Without an override the server uses the newest installed version under `/Applications` with the application's bundle
identifier. An override that names another application is refused with `APP_IDENTITY_MISMATCH`.

## Security

The server speaks MCP over stdio, sends no telemetry and uses no accounts. It controls Character Animator with the
Accessibility and, for `capture`, Screen Recording permissions of the MCP host, so run it only for clients you
trust. Tool paths are confined to the workspace, and the tools that change the project refuse any project that is
not an owned copy. See the [security model](docs/character-animator-mcp/source/pages/security/model.md) and
[SECURITY.md](SECURITY.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, checks and the rules for changes. This project follows
the [Code of Conduct](CODE_OF_CONDUCT.md).

## License

MIT. See [LICENSE](LICENSE).

## Trademarks

Adobe and Character Animator are either registered trademarks or trademarks of Adobe in the United States and/or
other countries. This project is not affiliated with, endorsed by, or sponsored by Adobe. It does not include or
redistribute Adobe software, puppets or project files; you supply your own licensed application.

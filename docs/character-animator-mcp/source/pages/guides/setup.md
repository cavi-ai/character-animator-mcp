# Setup

## Requirements

- macOS, Python 3.15 or newer and uv. On another platform the native tools are
  refused with `PLATFORM_UNSUPPORTED`.
- Adobe Character Animator, installed and signed in. The server uses the newest installed version under
  `/Applications` whose bundle identifier is `com.adobe.Character-Animator.application`;
  `CAVI_CHARACTER_ANIMATOR_APP` names a specific `.app` instead.
- The Swift command-line compiler (`xcode-select --install`). The server compiles its native helper on first
  use.
- Accessibility access for the MCP host. `capture` also needs Screen Recording access.

## Install

```sh
uv tool install cavi-character-animator-mcp
```

Upgrade with `uv tool upgrade cavi-character-animator-mcp`. The command is `cavi-character-animator-mcp`.

## Register the server

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

`CAVI_ADOBE_WORKSPACE` is required and must be an absolute path. Every tool path is relative to it and must stay
inside it. A desktop client that does not inherit your shell's `PATH` needs the
absolute path that `command -v cavi-character-animator-mcp` prints.

## Check the install

Call `character_status`. It reports `available`, `connected` and the native state:

- `available` is `false` with a `reason` when the application is not installed, the override names another
  application, or the helper cannot be built.
- `connected` is `true` when the application is running, its process id is known and the host has Accessibility
  access. Otherwise `reason` says to start the application and check the local control permissions.

The first call that reaches the native helper compiles it. The build is cached under the private data directory
(`CAVI_ADOBE_DATA`) in a folder named by the SHA-256 of the packaged source, with a receipt naming the source and
the binary. A cache that does not match its receipt is refused with `NATIVE_HELPER_UNSAFE`; remove the named
folder to rebuild it.

`character_status` never starts Character Animator. `project_open_prepared_copy` is the one tool that does.

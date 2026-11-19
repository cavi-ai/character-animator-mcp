# Contributing

This project follows the [Code of Conduct](CODE_OF_CONDUCT.md).

## Setup

Install Python 3.15 or newer and [uv](https://docs.astral.sh/uv/), then:

```bash
git clone https://github.com/cavi-ai/character-animator-mcp.git
cd character-animator-mcp
uv sync --locked --dev
```

The unit tests and the simulated evaluations need no Adobe application. The helper build test needs macOS and the
Swift command-line compiler.

## Checks

```bash
uv run --locked ruff check .
uv run --locked python -m unittest discover -s tests
uv run --locked python -m scripts.docs.build
uv run --locked python -m scripts.docs.verify
```

The documentation tests build and verify `docs/character-animator-mcp/source`, and fail when the README tool table
or the tool reference differs from the registered tools, or when the error codes in
`reference/results-and-errors.md` differ from the codes a client receives. The build writes
`docs/character-animator-mcp/v<version>`, which is not committed. Change the documentation in the same pull
request as the code.

The evaluations need Node.js and the MCP Eval executable (`npm install`, or `MCPEVAL_EXECUTABLE` set to a build of
[cavi-ai/mcp-eval](https://github.com/cavi-ai/mcp-eval)):

```bash
npm install --no-audit --no-fund --package-lock=false
npm run eval
```

## Where changes go

- `server.py` registers the tools and their typed results.
- `animator.py` holds project ownership, copies and the operation journals; `bridge.py` talks to the native helper.
- `character_native.swift` is the helper; `native.py` compiles it on first use.
- `media.py` validates exported PNG and WAV files and writes their receipts.
- `docs/character-animator-mcp/source` holds the documentation and `scripts/docs` builds it.

Add a line under Unreleased in `CHANGELOG.md`. Versions come from git tags and are never edited in a pull request.

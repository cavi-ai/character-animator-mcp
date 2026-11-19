# Security Policy

## Reporting a vulnerability

Report vulnerabilities privately through GitHub's private vulnerability reporting:
<https://github.com/cavi-ai/character-animator-mcp/security/advisories/new>. Do not open a public issue.
Include affected versions, reproduction steps and impact. Do not include Adobe account details or project files.

## Supported versions

Until 1.0, security fixes go to the latest minor release and `main`.

## Scope

- The server controls Character Animator through a native helper that uses Accessibility and, for capture, Screen
  Recording access, with the user's permissions. Connect it only to clients you trust.
- Tool paths are relative to the workspace folder named by `CAVI_ADOBE_WORKSPACE`.
- The helper is compiled from the packaged source and its build is pinned to that source's hash.
- The server speaks MCP over stdio, sends no telemetry and uses no accounts.
- Adobe applications and their licenses are out of scope; report those to Adobe.

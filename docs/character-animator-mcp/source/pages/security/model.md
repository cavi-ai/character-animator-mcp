# Security model

## The server acts with your permissions

The native helper controls Character Animator through macOS Accessibility, and `capture` reads the window through
Screen Recording access, with the permissions of the MCP host. It can press the menus and choosers of the
application the way you can. Connect the server only to clients you trust. Tools that change the project are
annotated destructive for that reason.

The server does not grant itself access. `capture` without Screen Recording access fails with
`SCREEN_PERMISSION_UNAVAILABLE` and makes no permission request. An authentication or permission prompt in the
application stops the operation with `AUTHENTICATION_BOUNDARY`; the server sends no input to it, signs into no
account, and records no camera or microphone.

## Files

Every tool path is relative to `CAVI_ADOBE_WORKSPACE`. Paths with `..`, symbolic links or control characters are
refused, export recipes refuse URLs, and the workspace root itself is not a valid path. Outputs (copies, captures, exports,
handoffs) are written only to paths that do not exist yet; nothing is overwritten.

A project copy is made with an exclusive rename, so a destination created meanwhile is never replaced. The project
tree must hold only regular files and directories. Imported files are copied to the private data directory,
hashed before and after, made read-only, and the copy is what Character Animator imports.

Export recipes pin every file by SHA-256. A file that changes while a recipe is inspected, or between inspection and
ingest, refuses the call.

## Ownership

A mutation needs a lease, and a lease covers one owned project copy: the folder's device and inode are recorded
and must still match. The tools that change the project refuse a project that is not an owned copy;
`project_save_copy` is the exception, and it writes a new project without editing the source scene. Leases and operation records are kept in the private data directory with owner-only permissions on their folders;
keep them private. They hold project paths and file hashes.

## Applications

The server starts no other Adobe application and does not install software. Starting the server never launches
Character Animator. `project_open_prepared_copy` launches it on one prepared copy. The helper is compiled from the
packaged source with the Swift compiler on first use, and each build is pinned to the SHA-256 of that source: a
cache that does not match its receipt is refused, never replaced.

## No background activity

The server speaks MCP over stdio. It makes no network connections, sends no telemetry, uses no accounts and does not
accept terms. It does not retry a call by itself: a native command that was dispatched is never replayed, and an
unknown outcome stays recorded until you resolve it.

## Reporting a problem

Report vulnerabilities privately as described in the repository's
[SECURITY.md](https://github.com/cavi-ai/character-animator-mcp/blob/main/SECURITY.md).

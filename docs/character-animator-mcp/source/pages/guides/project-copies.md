# Project copies and ownership

The server changes only a project copy it owns. A copy is made from a closed project, opened by the server, and
claimed with a lease. Every tool that changes the project takes that lease's ID.

## Make a copy

`project_prepare_copy` copies a closed `.chproj` project folder into a new folder in the workspace.

- The source holds exactly one regular `.chproj` file and its `Ch Data` folder, with no symbolic links.
- Character Animator must not have the source open: at most one application process may run, and none of its
  project roots may be the source.
- The destination does not exist, its parent does, and its name is a letter followed by up to 63 ASCII letters,
  digits, `_` or `-`. It is not inside the source and the source is not inside it.
- A tree has at most 8192 entries. The file receipt covers at most 4096 files and 1 GiB.

The copy is made in a hidden folder next to the destination, compared with the source file by file, then
published to the destination with an exclusive rename that never replaces anything. The source is checked again
for changes while it was copied. The result carries the `prepared_copy_id`, the device and inode of both folders
and the SHA-256 and size of every file. The same data is kept in a private receipt that the next tools read; the
ID is the only handle.

If a failure comes after the destination was published, the call ends with an unknown outcome: inspect the
destination before trying again.

## Open and claim it

1. `project_open_prepared_copy` with the `prepared_copy_id`. It checks the copy's bytes and structure against the
   receipt, requires that no Character Animator process, lease or operation is active, records the operation, and
   asks the application to open the project file.
2. `inspect`, and read `project_id` from the result. It is derived from the application's bundle identifier,
   process id, launch time and project roots, so it changes when the application restarts or another project
   opens.
3. `session_control` with `action` `claim`, an `owner` of 1 to 128 printable characters, `expected_project` set
   to that `project_id`, and the `prepared_copy_id`. The server checks that exactly the copy is open in one
   application process, without a permission prompt, then writes the lease.

The lease holds the owner, the project, the expiry and the owned root. `ttl_seconds` is 30 to 3600 and defaults to
600. While a lease is active, a second claim is refused. A claim is also refused while an operation is unresolved,
except for the matching unknown `project_open_prepared_copy` that the claim itself settles.

## Keep or end the lease

| Action | What it needs | What it does |
|---|---|---|
| `renew` | the active `lease_id` and the same open project | Extends the expiry by `ttl_seconds`. |
| `release` | the `lease_id`, and no unresolved operation | Deletes the lease. When the lease has expired or its project is no longer the open one, release is accepted only for an owned copy whose application has stopped: two stable observations of no process, and the owned root unchanged. |
| `resume` | the expired `lease_id`, the same `owner`, `expected_project`, and the `pending_operation_id` of the unknown operation | Issues a new `lease_id` after checking the same process and the sole owned root. It dispatches no native command. |
| `inspect` | nothing | Reports the project, the lease owner and expiry, and the pending operation. |

## Claim an open project, then save a copy

`session_control` `claim` without a `prepared_copy_id` claims whatever project is open, but a lease like that has
no owned root and every tool that changes the project is refused with "First save or open a new owned project copy
and verify its native identity". `project_save_copy` is the exception. It drives the application's Save Project As
into a new project folder:

```json
{"tool": "project_save_copy", "arguments": {"directory": "projects", "name": "Hero_work", "lease_id": "<lease_id>"}}
```

`directory` is an existing workspace folder, `name` is the same kind of safe ASCII name, and the destination must
not exist. When the application's project root becomes the new folder and it holds one `.chproj` file and a
`Ch Data` folder, the lease's owned root becomes that folder. The result lists `project_root`, `project_file` and
the files with their hashes. `original_source_hash` is `null`: the original file's hash is not available.

## What a mutation checks

`project_save_copy` aside, `import_media`, `project_select`, `scene_action` and `scene_export` are refused unless:

- the `lease_id` matches an unexpired lease for the project that is open now;
- no operation is unresolved;
- where the tool takes an `expected_fingerprint`, it equals the application's current state fingerprint;
- the application shows exactly the owned root, and that folder's device and inode are the ones recorded.

Each accepted call records its operation before it dispatches anything native; see
[Recovery and unknown outcomes](recovery.md).

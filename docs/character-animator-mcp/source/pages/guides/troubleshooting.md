# Troubleshooting

## `character_status` reports `available` `false`

`reason` holds the cause. The application is not installed (`APP_UNAVAILABLE`), `CAVI_CHARACTER_ANIMATOR_APP` names
a different application (`APP_IDENTITY_MISMATCH`; an override is final and never replaced by another install), the
platform is not macOS (`PLATFORM_UNSUPPORTED`), or the native helper cannot be built (below).

## `connected` is `false`

The application is not running, or the MCP host has no Accessibility access. Start Character Animator and grant
Accessibility access to the host in System Settings. The server never starts the application for a status call and
never asks for the permission itself.

## "Set CAVI_ADOBE_WORKSPACE to the absolute workspace directory"

The variable is missing. "`CAVI_ADOBE_WORKSPACE` must be an absolute path" means it is set to a relative path. Set
it in the `env` of the server's entry in the MCP client.

## `NATIVE_HELPER_UNAVAILABLE`, `NATIVE_HELPER_BUILD_FAILED`, `NATIVE_HELPER_UNSAFE`

- `NATIVE_HELPER_UNAVAILABLE`: the Swift compiler is missing (`xcode-select --install`) or the packaged helper
  source is not a regular file.
- `NATIVE_HELPER_BUILD_FAILED`: the compile failed or ran longer than 300 seconds. The message ends with the end of
  the compiler's error output. A failed build leaves no cache, so the next call compiles again.
- `NATIVE_HELPER_UNSAFE`: the cached build under `CAVI_ADOBE_DATA` does not match its receipt, or the cache folder
  is a symbolic link. The server refuses it and never replaces it. Remove the folder the message names and call
  again.

## "Another Character Animator request is still active"

A request holding the session lock for this workspace did not finish within 15 seconds. Wait for it, or inspect
with `inspect`, which does not take the lock.

## "Use a path inside the shared workspace without traversal, symlinks or control characters"

A path is outside the workspace, contains `..`, passes through a symbolic link or contains a control character.
Paths are relative to `CAVI_ADOBE_WORKSPACE`. "Output must not already exist" means an output directory or copy
destination already exists; every output goes to a new path.

## "A current matching lease is required"

There is no lease, it expired, the `lease_id` is wrong, or the open project is no longer the one the lease was
claimed for. Check `session_control` `inspect`, then `renew` or claim again.

## "First save or open a new owned project copy and verify its native identity"

The lease owns no project copy. Prepare and open a copy, or save one with `project_save_copy`. See [Project copies
and ownership](project-copies.md). "The owned project root inode changed after ownership was verified" means the
owned folder was replaced; the lease no longer covers it.

## "Observed selection or native state changed; inspect again before acting"

The `expected_fingerprint` is not the application's current one. Call `inspect` and use its new
`native.state.fingerprint`. When the state changes between the check and the native command, the helper reports
`STALE_STATE`, and the message ends with up to five differences ("changed native state: ...").

## "An unresolved native command blocks further mutations"

An earlier operation is in the journal. See [Recovery and unknown outcomes](recovery.md).

## "Native request was interrupted; inspect the app and operation journal"

A native request was cancelled, took longer than 45 seconds or wrote more than 4 MiB. The outcome is unknown: check
the application and the journal before anything else. "Native adapter did not return a bounded successful
response" and "Native adapter returned an invalid response" are the same class.

## "An unrelated native modal blocks import" and chooser or focus codes

A dialog other than the Import chooser is open in Character Animator. Close it in the application. The helper
reports its own codes for what it observed: `UNEXPECTED_MODAL` asks you to resolve the current modal before another
command, `CHOOSER_MISMATCH` means the chooser's title differs from the requested operation, `FOCUS_CHANGED` and
`FOCUS_UNAVAILABLE` mean the chooser or the application could not be kept in front, and `AUTHENTICATION_BOUNDARY`
means a sign-in or permission prompt must be handled by you: the server sends no input to one.

## `capture` fails

`SCREEN_PERMISSION_UNAVAILABLE` means Screen Recording access is absent; the server makes no permission request.
`WINDOW_UNAVAILABLE` means no Character Animator window is available, and `APPLICATION_UNAVAILABLE` that it is not
running.

## `PROJECT_ITEM_AMBIGUOUS`

The helper expects exactly one visible Project-panel row with that `name` and `item_type`, found by recognized
text. The message lists the rows it read. Make the row visible in the Project panel, or give the item a name no
other row shares.

## An import or export shows `completion` `unverified`

The server waited and did not see the result. For an import, no new puppet or audio row became visible in the
Project panel: scroll the panel so the row shows and call `inspect`. Without Screen Recording access the rows
cannot be read. For an export, the frames, WAV and sidecars did not all appear and settle within 300 seconds:
check the directory with `export_inspect`.

# Your first result

This walks one saved project from a closed folder to an inspected export. The paths are relative to the
workspace (`CAVI_ADOBE_WORKSPACE`); replace `projects/Hero` with a closed project folder of yours. It holds one
`.chproj` file and its `Ch Data` folder, and Character Animator has it closed.

Each call below is a tool call with these arguments. Copy the IDs and the state fingerprint from the previous
result; the server never guesses them.

## 1. Check the application

```json
{"tool": "character_status", "arguments": {}}
```

`available` and `connected` are both `true` when the application runs with Accessibility access. With the
application closed, `available` is `true` and `connected` is `false`; that is what the next step expects.

## 2. Prepare a copy

```json
{"tool": "project_prepare_copy", "arguments": {"source": "projects/Hero", "destination": "projects/Hero_work"}}
```

The result has `status` `prepared_copy`, a `prepared_copy_id` and the SHA-256 and size of every file in the new
copy under `files`. `projects/Hero` is untouched. The server refuses the call while the source is open in
Character Animator.

## 3. Open the copy

```json
{"tool": "project_open_prepared_copy", "arguments": {"prepared_copy_id": "<prepared_copy_id>"}}
```

This launches Character Animator on the copy. `status` `prepared_copy_opened` with `completion` `observed` means
the application's open project root is the copy. `prepared_copy_open_requested` with `completion` `unverified`
means the request was sent but the root was not yet observed; call `inspect` before going on.

## 4. Inspect and claim

```json
{"tool": "inspect", "arguments": {}}
```

Copy `project_id` from the result. Then claim the project with a name for your session:

```json
{"tool": "session_control", "arguments": {"action": "claim", "owner": "my-session",
 "expected_project": "<project_id>", "prepared_copy_id": "<prepared_copy_id>"}}
```

The result has `state` `owned`, a `lease_id` and `expires_at`; the lease lasts 600 seconds unless `ttl_seconds`
(30 to 3600) says otherwise. Renew it with `action` `renew` before it ends.

## 5. Select and act

`inspect` returns the native state; its `native.state.fingerprint` is the 64-character fingerprint of what the
application shows now. Select a scene row, then run a menu action on the selection, each with the latest
fingerprint:

```json
{"tool": "project_select", "arguments": {"name": "Scene 1", "item_type": "scene", "extend": false,
 "expected_fingerprint": "<fingerprint>", "lease_id": "<lease_id>"}}
{"tool": "inspect", "arguments": {}}
{"tool": "scene_action", "arguments": {"action": "compute_lip_sync", "expected_fingerprint": "<new fingerprint>",
 "lease_id": "<lease_id>"}}
```

Both results report `completion` `unverified`: the menu was dispatched. Look at the application with `capture`
or `inspect` to see the outcome before the next step. A fingerprint that no longer matches the application is
refused before anything is dispatched, with the message "Observed selection or native state changed; inspect again
before acting".

## 6. Export and check the files

```json
{"tool": "inspect", "arguments": {}}
{"tool": "scene_export", "arguments": {"directory": "exports/hero", "name": "Hero",
 "expected_fingerprint": "<fingerprint>", "lease_id": "<lease_id>"}}
```

`exports/hero` must not exist. The result lists `expected_output_directory` and `expected_xml` and says to use
`export_inspect` once the PNG and WAV files appear. Write an export recipe that names each frame and the WAV with
its SHA-256 (see [Importing and exporting](importing-and-exporting.md)), then:

```json
{"tool": "export_inspect", "arguments": {"recipe": "exports/hero/recipe.json"}}
{"tool": "export_ingest", "arguments": {"recipe": "exports/hero/recipe.json", "directory": "exports/hero_handoff"}}
```

`export_inspect` returns `status` `inspected`, the frame count and duration, and `native_export`
`not_verified`. `export_ingest` writes the pinned media receipt, the audio descriptor and `handoff.json` into the
new directory and returns their paths and hashes.

## Release the lease

```json
{"tool": "session_control", "arguments": {"action": "release", "lease_id": "<lease_id>"}}
```

Release is refused while an operation is unresolved; see [Recovery and unknown outcomes](recovery.md).

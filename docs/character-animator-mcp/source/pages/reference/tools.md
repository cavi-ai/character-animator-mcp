# Tools

Every tool is listed with its parameters and the fields of its result. A parameter marked `*` is required.
Access is what the tool annotations declare: `read-only` changes nothing, `write` creates files or records
ownership and operations, `destructive` changes the open project or the application. Paths are relative to the
workspace (`CAVI_ADOBE_WORKSPACE`) and must stay inside it. IDs (`prepared_copy_id`, `operation_id`) are 32
lowercase hexadecimal characters; an `expected_fingerprint` is the 64-character `native.state.fingerprint` of the
latest `inspect`.

A tool that fails raises an error with the reason. The error shape and codes are in
[Results and errors](results-and-errors.md). Results of tools that report an operation carry `retry_safe`, which
is always `false`: the server never says that repeating a call is harmless.

## Observe

| Tool | Access | Parameters | Result | What it does |
|---|---|---|---|---|
| `character_status` | read-only |  | `available`, `connected`, `native`, `reason`, `launches_application` | Whether the application is installed, running and reachable. A missing application is reported in `reason`, not raised. |
| `inspect` | read-only |  | `project_id`, `native`, `pending_operation`, `project_items`, `project_items_error`, `timeline_selection`, `launches_application` | The process, the open project roots, the native controls and prompts, and the unresolved operation journal record or `null`. `project_items` lists the Project panel rows visible in the window, each with `name` and `type` (`puppet`, `audio` or `scene`), read by text recognition; it needs Screen Recording access and is `null` with the reason in `project_items_error` without it. `timeline_selection` is whether Timeline > Set Work Area to Selection is enabled, which it is while timeline tracks are selected, or `null` when the menu item is not found. |
| `capture` | write | `directory`* | `path`, `sha256`, `native`, `identity`, `launches_application` | Captures only the Character Animator window, with recognized text and geometry, into `directory/character.png`, and returns that PNG as image content, scaled to at most 1568 px on its long side. `directory` must not exist. `identity` is `observed_window_and_ocr`. |

`launches_application` is `false` for these tools. `character_status` has `native` `null` when the helper
reported a rejection.

## Ownership and projects

| Tool | Access | Parameters | Result | What it does |
|---|---|---|---|---|
| `session_control` | write | `action`*, `owner`, `expected_project`, `lease_id`, `ttl_seconds`, `pending_operation_id`, `prepared_copy_id` | `project_id`, `lease_id`, `owner`, `expires_at`, `state`, `pending_operation`, `prepared_copy_id`, `owned_root` | `action` is `inspect`, `claim`, `renew`, `release` or `resume`. `ttl_seconds` is an integer from 30 to 3600, default 600. `state` is `owned` or `unclaimed`. `lease_id` is returned by `claim`, `renew` and `resume`; `prepared_copy_id` and `owned_root` by a lease claimed from a prepared copy. |
| `project_prepare_copy` | write | `source`*, `destination`* | `status`, `prepared_copy_id`, `source`, `destination`, `source_identity`, `destination_identity`, `files`, `launches_application` | Copies a closed saved `.chproj` project folder to a new workspace folder and verifies the file hashes. `status` is `prepared_copy`; `files` lists `path`, `sha256` and `bytes`. |
| `project_open_prepared_copy` | write | `prepared_copy_id`* | `status`, `completion`, `prepared_copy_id`, `operation_id`, `project_id`, `native`, `retry_safe`, `launches_application` | Opens the exact prepared copy in Character Animator, which it launches. `status` is `prepared_copy_opened` with `completion` `observed`, or `prepared_copy_open_requested` with `completion` `unverified` and `project_id` `null`. |
| `project_save_copy` | destructive | `directory`*, `name`*, `lease_id`* | `status`, `operation_id`, `project_id`, `project_root`, `project_file`, `files`, `source_identity`, `retry_safe` | Native Save Project As into a new project folder `directory/name`, then verifies the application's project root and the project files. `directory` exists; `name` is 1 to 64 ASCII letters, digits, `_` or `-`, starting with a letter. `status` is `owned_copy`. The result also has `original_source_hash`, always `null`, and `native`. |
| `project_select` | destructive | `name`*, `item_type`*, `extend`*, `expected_fingerprint`*, `lease_id`* | `operation_id`, `status`, `name`, `item_type`, `extend`, `expected_state_fingerprint`, `selection_evidence`, `native`, `completion`, `retry_safe` | Selects one Project-panel row by `name` and `item_type` (`puppet`, `audio` or `scene`). `extend` is a boolean: `true` adds to the selection. `status` is `native_project_item_selected`, `completion` `unverified`. |

## Import and scene

| Tool | Access | Parameters | Result | What it does |
|---|---|---|---|---|
| `import_media` | destructive | `source`*, `kind`*, `lease_id`* | `operation_id`, `status`, `completion`, `kind`, `source`, `import_copy`, `project_item`, `native`, `source_identity`, `retry_safe` | Imports a hash-pinned workspace PSD (`kind` `puppet_psd`) or WAV (`audio_wav`) into the owned project and waits, up to 120 seconds, until no modal is open and File > Import is enabled again. `source` and `import_copy` carry `path`, `sha256` and `bytes`. `status` is `native_import_submitted`. `completion` is `observed` when a puppet or audio row that was not visible before appears in the Project panel, given in `project_item`, a row named after the source file first; otherwise `unverified` and `project_item` `null`. The first WAV after a project opens is `unverified`: its row is drawn only once the Project panel is clicked. The result also has `native_after`, the observation after the wait. |
| `scene_action` | destructive | `action`*, `expected_fingerprint`*, `lease_id`* | `operation_id`, `status`, `action`, `completion`, `expected_state_fingerprint`, `project_item`, `native_dispatch`, `native_after`, `selection_identity`, `retry_safe` | One fixed menu action on the current selection: `add_to_new_scene`, `create_take_from_scene_audio`, `compute_lip_sync`, `set_work_area_to_selection` or `export_png_wav`. Except for `export_png_wav`, whose chooser stays open for `scene_export`, it waits up to 120 seconds for the application to finish. `status` is `native_scene_action_submitted`. `add_to_new_scene` is `completion` `observed` when a new scene row appears in the Project panel, given in `project_item`; every other action is `unverified`. `set_work_area_to_selection` spans the work area over the selected timeline tracks or take bars; while the work area is enabled, `scene_export` exports only that range. |
| `scene_export` | destructive | `directory`*, `name`*, `expected_fingerprint`*, `lease_id`* | `operation_id`, `status`, `native`, `retry_safe` | Exports a PNG Sequence and WAV of the owned scene into the new workspace directory `directory`. `name` is 1 to 48 ASCII letters, digits, `_` or `-`, starting with a letter. It waits up to 300 seconds for `directory/name/name.000.png` onward, `directory/name/name.wav`, `directory/name/name.json` and `directory/name.xml`. `completion` is `observed` once the frames are numbered without a gap, every file exists and nothing changed between two checks while the application was idle; the result then has `frame_count`, `frames` (`first` and `last`), `wav`, `json` and `xml`. Otherwise `completion` is `unverified` with `output_verification`. The result also has `directory`, `name`, `expected_output_directory`, `expected_xml` and `native_submission`; `status` is `native_export_submitted`. |

## Recovery

| Tool | Access | Parameters | Result | What it does |
|---|---|---|---|---|
| `operation_control` | write | `action`*, `operation_id`*, `lease_id`, `user_confirmed_cancelled` | `operation_id`, `status`, `native`, `retry_safe` | `action` is `inspect`, `verify_copy`, `continue_copy`, `continue_import`, `continue_export`, `confirm_cancelled_import`, `reconcile_import`, `cancel_unsubmitted`, `reconcile_unsubmitted_copy`, `reconcile_copy_after_exit` or `abandon_after_exit`. `inspect` returns the journal record as `operation` with `status` set to its state. `confirm_cancelled_import` asks the user when the client supports elicitation; otherwise it needs `user_confirmed_cancelled`, a boolean, default `false`, set to `true`. Its result carries `confirmation`: `elicited` or `caller_reported`. `reconcile_import` resolves an unknown import as `native_import_observed`, `completion` `observed`, with `project_item`, when no chooser or modal is open and the Project panel shows a row of the import's type that was not visible before it. The other results are described in [Recovery and unknown outcomes](../guides/recovery.md). |

## Export files

| Tool | Access | Parameters | Result | What it does |
|---|---|---|---|---|
| `export_inspect` | read-only | `recipe`* | `schema`, `version`, `status`, `name`, `fps`, `frame_count`, `duration`, `frame_order_source`, `frame_rate_source`, `native_export`, `launches_applications` | Validates the PNG frames, the WAV and the source files named by the recipe against their hashes, and the dialogue sample timing. It writes nothing and does not run a native export. `schema` is `cavi.character-export.v1`, `status` `inspected`, `native_export` `not_verified`. |
| `export_ingest` | write | `recipe`*, `directory`* | `schema`, `version`, `status`, `name`, `media_receipt`, `cutscene_audio`, `handoff`, `native_export`, `launches_applications` | Inspects the recipe and writes a pinned media receipt and a measured PCM audio descriptor into the new directory `directory`. `schema` is `cavi.character-handoff.v1`, `status` `ingested`. `media_receipt` and `handoff` carry `path` and `sha256`; `cutscene_audio` is `null` without audio. |

`export_inspect` also returns `loop`, `alpha`, `recipe`, `frames`, `audio`, `audio_timing_source`, `source_roles`,
`inputs` and `xml_timing` (`not_interpreted`). `export_ingest` also returns `fps`, `frame_count`, `duration`,
`frame_order_source`, `frame_rate_source`, `audio_timing_source`, `source_roles`, `inputs` and `xml_timing`. The
recipe format is in [Importing and exporting](../guides/importing-and-exporting.md#write-an-export-recipe).

## Access

`character_status`, `inspect` and `export_inspect` are read-only. `capture`, `session_control`,
`project_prepare_copy`, `project_open_prepared_copy`, `operation_control` and `export_ingest` are write.
`project_save_copy`, `import_media`, `scene_action`, `scene_export` and `project_select` are destructive. No tool
reaches beyond the local machine and the application it drives.

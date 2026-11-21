# Importing and exporting

Every call here needs the `lease_id` of an owned project copy; see [Project copies and
ownership](project-copies.md). An import, a new scene and an export wait for Character Animator to finish and
report `completion` `observed` when the server sees the new Project row or the written files, otherwise
`unverified`. `export_inspect` and `export_ingest` report `native_export` `not_verified`: they check files, not
how Character Animator made them.

## Import a puppet or dialogue

```json
{"tool": "import_media", "arguments": {"source": "art/Hero.psd", "kind": "puppet_psd", "lease_id": "<lease_id>"}}
{"tool": "import_media", "arguments": {"source": "audio/line1.wav", "kind": "audio_wav", "lease_id": "<lease_id>"}}
```

`source` is a workspace file whose extension matches `kind` (`.psd` or `.wav`). It must be a regular file, not
empty and at most 1 GiB. The server hashes it, makes a read-only copy in its private data directory, hashes the
copy and the source again, and imports the copy. The result lists the `source` and the `import_copy` with `path`,
`sha256` and `bytes`.

- A PSD goes through the application's Import chooser. A WAV is handed to the already running application; a
  WAV handoff whose outcome is uncertain is never replayed through the chooser.
- The server reads the visible Project panel rows before the import and waits, up to 120 seconds, until no modal
  is open and File > Import is enabled again. `completion` `observed` comes with `project_item`, the new puppet or
  audio row, one named after the source file first. With `unverified`, the new row was not visible: scroll the
  Project panel and call `inspect`. Reading rows needs Screen Recording access.

If an Import chooser or its Go To sheet is already open for this project, the call adopts it instead of opening
the menu again. Any other modal blocks the import.

## Select and run a menu action

`project_select` selects one Project-panel row by `name` (1 to 128 printable characters) and `item_type`
(`puppet`, `audio` or `scene`). `extend` is required: `true` adds to the selection. The row is found by its
recognized text; two matches are refused with `PROJECT_ITEM_AMBIGUOUS`. The `selection_evidence` in the result is
visual evidence, not a scene ID.

`scene_action` runs one fixed menu action against the current selection: `add_to_new_scene`,
`create_take_from_scene_audio`, `compute_lip_sync`, `set_work_area_to_selection` or `export_png_wav`, and waits
for the application to finish. `add_to_new_scene` is `completion` `observed` with the new scene row in
`project_item`. `inspect` reports `timeline_selection` `true` while timeline tracks or take bars are selected;
`set_work_area_to_selection` then spans the work area from the earliest to the latest selected time. While the
work area is enabled, `scene_export` exports only that range. Both tools take an
`expected_fingerprint` copied from the latest `inspect` (`native.state.fingerprint`). The result's
`expected_state_fingerprint` repeats it, and `native_after` (`scene_action`) or `native` (`project_select`) is the
state observed after the dispatch.

## Export a scene

```json
{"tool": "scene_export", "arguments": {"directory": "exports/hero", "name": "Hero",
 "expected_fingerprint": "<fingerprint>", "lease_id": "<lease_id>"}}
```

`directory` must not exist and its parent must. `name` is a letter followed by up to 47 ASCII letters, digits, `_`
or `-`. The server creates `directory`, then submits the Export Scene chooser with `name` for the owned scene.
The result reports `status` `native_export_submitted`, `expected_output_directory` (`directory/name`) and
`expected_xml` (`directory/name.xml`). The server then waits, up to 300 seconds, for `name.000.png` onward,
`name.wav` and `name.json` in `directory/name` and for `directory/name.xml`. Once the frames are numbered without
a gap, every file exists and nothing changed between two checks while the application was idle, `completion` is
`observed` with `frame_count`, `frames` (`first` and `last`), `wav`, `json` and `xml`. Otherwise it is
`unverified`, and `output_verification` says to use `export_inspect` once the files appear. If the chooser was
not submitted the operation stays recorded as unknown; see [Recovery and unknown outcomes](recovery.md).

## Write an export recipe

`export_inspect` and `export_ingest` read a JSON recipe of at most 4 MiB. Order, frame rate and sample timing are
yours to declare; the server never guesses them.

```json
{
  "schema": "cavi.character-export.v1",
  "version": 1,
  "name": "Hero",
  "loop": false,
  "alpha": "straight",
  "frame_rate": {"numerator": 24, "denominator": 1},
  "frames": [
    {"name": "Pose01", "path": "exports/hero/Hero/frame_0001.png", "sha256": "<sha256 of the file>"},
    {"name": "Pose02", "path": "exports/hero/Hero/frame_0002.png", "sha256": "<sha256 of the file>"}
  ],
  "audio": {"path": "exports/hero/Hero.wav", "sha256": "<sha256 of the file>",
            "start": 0, "clip_in_samples": 0, "duration_samples": 4800},
  "source_roles": [
    {"role": "project", "path": "projects/Hero_work/Hero.chproj", "sha256": "<sha256 of the file>"}
  ]
}
```

The paths are placeholders; use the names of the files the export wrote.

- `schema` and `version` are fixed. `loop` is a boolean and `alpha` is `straight`. Any other top-level key is
  refused.
- `frame_rate` is a rational of 1 to 120 frames per second, each number an integer up to 120000.
- `frames` lists 1 to 1000 PNGs in playback order. Each has exactly `name`, `path` and `sha256`. Names are a letter
  followed by up to 47 ASCII letters, digits, `_` or `-`, and unique. Paths are distinct workspace PNG files,
  not URLs; a pose that repeats is a separate exported file. Each PNG is at most 64 MiB, 8-bit RGBA and a single
  image.
- The duration is the frame count times `denominator` over `numerator` and is at most 300 seconds.
- `audio` is optional. It names a PCM WAV of at most 64 MiB and at most 300 seconds, mono or stereo, 8 to 192 kHz,
  integer samples of 1 to 4 bytes or 32-bit float samples (the PNG Sequence and WAV export writes 32-bit float),
  together with `start` (seconds, 0 to 300), `clip_in_samples` and
  `duration_samples`. The clip must lie inside the WAV and end no later than the frames do.
- `source_roles` lists up to 62 files that stay with the export, each with a `role` of `project`, `puppet`,
  `performance`, `export_xml`, `export_receipt`, `artwork` or `dialogue_source`, and distinct paths. The server
  hashes them and does not read their contents; the XML timing is not interpreted.
- Every `sha256` is checked against the file, and again at the end of the call. A file that changed refuses the call.

## Inspect and ingest

`export_inspect` returns what it found without writing anything: `status` `inspected`, the frames in the declared
order with their sizes and hashes, `frame_count`, `duration`, `fps` reduced to lowest terms, the audio with its
measured `sample_rate`, `channels`, `sample_width`, `sample_format` (`integer` or `float`) and `samples`, the `source_roles` and every input's hash in
`inputs`. `frame_order_source` is `explicit_recipe` and `frame_rate_source` is `caller_declared`. `native_export` is
`not_verified` and `launches_applications` is `false`.

`export_ingest` runs the same inspection and writes a new directory (it must not exist) holding:

- `media-input.json`, the recipe handed to the shared media receipt;
- `media/media.json`, the pinned animation media receipt of the frames and sources;
- `handoff.json`, the handoff result. Its `path` and `sha256` come back in the tool result as `handoff`.

`cutscene_audio` is the audio with a `sources` list naming the media receipt, the recipe and the source roles, or
`null` without audio. Ingest does not establish native rigging, lip-sync correctness, playback or visual
acceptance.

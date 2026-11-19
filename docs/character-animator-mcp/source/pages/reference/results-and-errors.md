# Results and errors

Every tool returns the result and error shapes of the
[MCP Core contract](https://github.com/cavi-ai/mcp-core/blob/main/docs/mcp-core/source/pages/reference/results-and-errors.md):
structured content that matches the tool's output schema, and on failure an `error` with `code`, `outcome`,
`retry_safe` and `next_action`. This page lists what this server adds.

## Results

A tool that reports an operation returns `retry_safe` `false`. A native command that was dispatched is reported with
`completion` `unverified` and a `status` such as `native_import_submitted`: the result proves what was submitted
and what the application showed afterwards, not that the work is done. Fields named `launches_application`
(`launches_applications` for the export tools) say whether the tool started Character Animator; only
`project_open_prepared_copy` returns `true`.

## Errors

A failed call is a tool error whose structured content has this shape:

```json
{"error": {"version": 1, "code": "STALE_STATE", "operation": "scene_action",
           "outcome": "rejected", "retry_safe": false, "next_action": "inspect_inputs"}}
```

`rejected` means nothing was dispatched to the application. `unknown` means a native command may or may not have
happened: the journal record stays, and `next_action` is `inspect_application_and_outputs`. The tools to do that
with are `inspect`, `operation_control` `inspect` and the output files; see [Recovery and unknown
outcomes](../guides/recovery.md).

### Codes

| `code` | `outcome` | `next_action` | When |
|---|---|---|---|
| `TOOL_NOT_FOUND` | `rejected` | `list_tools` | The tool name is not registered. |
| `INVALID_ARGUMENT` | `rejected` | `inspect_inputs` | The arguments fail the input schema or name an undeclared argument, or the server refused the request before dispatch: a path outside the workspace, an existing output, a missing or expired lease, a changed `expected_fingerprint`, an unresolved operation. |
| `INPUT_NOT_FOUND` | `rejected` | `inspect_inputs` | The tool raised `FileNotFoundError`. |
| `OUTCOME_UNKNOWN` | `unknown` | `inspect_application_and_outputs` | Anything that may have changed the application or the output: an interrupted or malformed native response, an unresolved step, a failed verification, or any other `OSError` or `RuntimeError`. |
| `PLATFORM_UNSUPPORTED` | `rejected` | `inspect_inputs` | The host is not macOS. |
| `APP_UNAVAILABLE` | `rejected` | `inspect_inputs` | Character Animator is not installed, or not at the path `CAVI_CHARACTER_ANIMATOR_APP` names. |
| `APP_IDENTITY_MISMATCH` | `rejected` | `inspect_inputs` | The application at that path is not Character Animator. |
| `NATIVE_HELPER_UNAVAILABLE` | `rejected` | `inspect_inputs` | The Swift compiler or the helper source is missing. |
| `NATIVE_HELPER_BUILD_FAILED` | `rejected` | `inspect_inputs` | The helper did not compile, or compiling timed out after 300 seconds. |
| `NATIVE_HELPER_UNSAFE` | `rejected` | `inspect_inputs` | The cached helper build failed its integrity check or the cache is a symbolic link. |
| `STALE_STATE` | `rejected` | `inspect_inputs` | The helper found the application state differs from the one the request was based on. When the helper returns its state, the message lists up to five differences. |

The native helper also reports codes of its own: `CHOOSER_MISMATCH`, `FOCUS_CHANGED`, `FOCUS_UNAVAILABLE`,
`AUTHENTICATION_BOUNDARY`, `PRECONDITION_CHANGED`, `DIRECTORY_NOT_OBSERVED`, `APPLICATION_UNAVAILABLE`,
`INPUT_NOT_OBSERVED`, `NATIVE_ACTION_FAILED`, `INVALID_DESTINATION`, `CAPTURE_FAILED`, `UNEXPECTED_MODAL`,
`PROJECT_ITEM_AMBIGUOUS`, `SCREEN_PERMISSION_UNAVAILABLE`, `DESTINATION_EXISTS` and others. Each arrives with the
helper's own `outcome`: `rejected` with `inspect_inputs` when the helper stopped before dispatching its command,
otherwise `unknown`. A native command that was dispatched and then failed is reported as `OUTCOME_UNKNOWN`. When
a step of a recorded operation fails after a native dispatch, the code is kept in the journal record under
`failure`, and the call ends with an `unknown` outcome whose message names that code.

`retry_safe` is `false` for every code.

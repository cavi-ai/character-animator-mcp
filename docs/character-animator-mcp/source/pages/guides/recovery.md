# Recovery and unknown outcomes

The server does not retry. A tool that changes the application writes the operation to a private journal before
it dispatches anything native, and clears the journal only when the operation finished. What the journal holds,
and what you may do next, depends on how far the call got.

## The operation journal

| State | Meaning |
|---|---|
| `pending` | The operation was recorded and nothing native was dispatched yet. |
| `observed` | The first native command was dispatched and its result observed. |
| `unknown` | A later step failed, was interrupted or could not be verified. The record keeps the failure `code` and `message`. |

A call that is refused before it dispatches anything, such as a stale fingerprint or a missing lease, leaves no
record and returns `rejected`. A call that completes archives its record under the operation's ID and
clears the journal. A record that stays blocks every later mutation with "An unresolved native command blocks
further mutations", and `session_control` `release` is refused until it is resolved.

A native request is interrupted when it is cancelled, runs longer than 45 seconds or writes more than 4 MiB.
The server then stops the helper and everything it started, and the call ends with an `unknown` outcome.

## Find out what happened

1. `inspect` returns `pending_operation`: the journal record, or `null`.
2. `operation_control` with `action` `inspect` and the `operation_id` returns the `status` (the journal state), the
   whole record as `operation` and the application's state as `native`.
3. Look at the application and at the output: `capture`, `inspect`, and for an export the files themselves with
   `export_inspect`.

Do not repeat the original call. Choose one of the recovery actions below, or resolve the situation in the
application and inspect again.

## Recovery actions

Every action takes the `operation_id`. All but `inspect` take the `lease_id` of the lease the operation ran under,
and need the operation to be `unknown`, except where noted. Most also need the same application process (process
id and launch time) the operation was recorded against; one whose process changed stays unresolved.

| `action` | Use it when | What it does |
|---|---|---|
| `inspect` | Always. | Returns the record and the application's state. |
| `verify_copy` | A Save As copy was submitted. | Checks that the application's project root is the expected new folder and that it holds one `.chproj` file and `Ch Data`. Returns `owned_copy` and makes that folder the owned root. |
| `continue_copy` | The Save As chooser is still open. | Resumes the exact existing Save As chooser. It does not repeat the menu command. |
| `continue_import` | The Import chooser or its Go To sheet is still open. | Resumes the existing chooser. It never replays File > Import, except for the one recorded failure before the menu was dispatched. |
| `continue_export` | The Export Scene or Go To chooser is still open. | Resumes only the journaled chooser and output directory. |
| `confirm_cancelled_import` | You cancelled the import in the application. | When the MCP client supports elicitation, the server asks you whether you cancelled the import; a decline or a no is rejected. Other clients need `user_confirmed_cancelled` set to `true`. It also needs matching process, root and source evidence. It sends no native command, and the result is `cancelled_user_reported` with `confirmation` `elicited` or `caller_reported`: the cancellation is your statement, not a native check. |
| `cancel_unsubmitted` | A Save As or Export Scene chooser was opened and nothing submitted. | Cancels that exact owned chooser, with no expected output in place. Returns `cancelled`. |
| `reconcile_unsubmitted_copy` | The first Save As stage was recorded and the chooser is closed. | Records the stage as closed without submission after stable source checks. It sends no native command and does not imply that you cancelled. |
| `reconcile_copy_after_exit` | The application exited after an initial Save As was submitted. | Resolves it only when the recorded process has exited, no Character Animator is running and the destination is still absent. Returns `destination_absent_after_process_exit`; it verifies no copy. The original lease is expired. |
| `abandon_after_exit` | The application exited with an unknown import, export or Save As on an owned project. | After two stable observations that every Character Animator process has exited, archives the unknown operation, expires the lease and keeps the project files. Returns `unknown_operation_abandoned` with `completion` `native_outcome_unknown`. |

Every action except `reconcile_copy_after_exit` and `abandon_after_exit` needs a lease that has not expired. Those
two read the original lease even after it expired. When the lease expired and the application is still running,
`resume` it first.

## Resume an expired lease

An expired lease does not erase the unknown operation. `session_control` with `action` `resume`, the expired
`lease_id`, the same `owner`, `expected_project` and `pending_operation_id` renews ownership and returns a new
`lease_id`. It checks the same process and the sole owned project root, and it dispatches no native command.
Continue with a recovery action above.

## After the application exits

Nothing in the journal changes when Character Animator quits. Start with `operation_control` `inspect`. An owned
project copy keeps its files: `abandon_after_exit` preserves them. A lease
that was not claimed from an owned copy cannot be abandoned; use `reconcile_copy_after_exit` for an initial Save As
and release the lease once the journal is clear.

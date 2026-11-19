# Testing and evaluation

No Adobe application is needed for the checks below, except the optional native background evaluation.

## Unit tests

```sh
uv sync --locked --dev
uv run --locked ruff check .
uv run --locked python -m unittest discover -s tests
uv run --locked python -m scripts.docs.build
uv run --locked python -m scripts.docs.verify
```

The ownership and operation tests drive the real `CharacterAnimator` and the real server over stdio with a scripted
native bridge; they establish the server's own rules, not Character Animator's behavior. They cover:

- ownership: claiming, renewing, releasing and resuming a lease, prepared copies, and refusals for a wrong owner,
  lease, process, project root or state fingerprint before any native dispatch;
- operations: Save As, import, export, selection and scene actions recorded before dispatch, unknown outcomes kept
  in the journal, the continue, cancel, reconcile and abandon actions, and refusal to replay an uncertain
  dispatch;
- the bridge: request identity, structured submission context on a failed continuation, and an interrupted request
  that stops what the helper started;
- the helper build: one build per source, a changed source builds beside the old one, concurrent builds compile
  once, a tampered or symbolic-link cache is refused, compiler failures and timeouts leave no build. The test that
  compiles the shipped Swift helper runs only on macOS with `swiftc`;
- export files: explicit frame order and sample timing, rejected ambiguous frames, remote paths, truncated or
  float WAV files and changed sources;
- the catalog: the registered tools match the list in the tests, unknown arguments are rejected, and the
  documented tools and result fields match [Tools](tools.md);
- documentation: the build is reproducible, the navigation lists every page once, every relative link resolves,
  the README tool table matches the registered tools and the error codes in
  [Results and errors](results-and-errors.md) match what a client receives.

## Evaluations

```sh
npm install --no-audit --no-fund --package-lock=false
npm run eval
```

`npm run eval` runs `evals/run.py`, which starts the server over stdio and runs the [MCP
Eval](https://github.com/cavi-ai/mcp-eval) probes. `MCPEVAL_EXECUTABLE` selects another `mcpeval` binary. The
reports go to `.tmp/evals/<run>/`.

| Mode | Script | What it runs |
|---|---|---|
| `protocol` | `npm run eval:protocol` | The server itself with `evals/character_animator.manifest.json`: at most 16 tools and 20,000 schema bytes, at most 8,000 tokens in total and 3,000 per tool, pagination within 2 pages, the declared surfaces, and a refusal of an unknown protocol version. |
| `simulated` | `npm run eval:simulated` | `evals/simulated_server.py`, the production tools with a synthetic native adapter that supports only `status` and `inspect`, with `evals/character_animator.inspection.manifest.json`. |
| `native-background` | `uv run --locked python evals/run.py --mode native-background` | The same inspection manifest against a running Character Animator. It accepts only the read-only `character_status` and `inspect` tools. |

`npm run eval` runs `protocol` and `simulated`. The run exits non-zero when a probe fails.

## Checked against Character Animator

The tests and the protocol and simulated evaluations do not start Character Animator, so they do not cover the
helper's menu and chooser handling, prepared-copy opening, imports or exports in the application. A change to the
helper source is tried in Character Animator. See [Version and support](../release/version-and-support.md).

# Pocket i desktop

This directory turns the accepted E007 research modules into one portable,
inspectable desktop core. It is intentionally standard-library Python at the
first checkpoint so the orchestration contract is identical on macOS, Windows
and Linux.

Checkpoint 1 contains the core and tests, not a finished application. Model
runtimes, real local-library adapters, network transport, UI and installers are
connected in later checkpoints from
[`DESKTOP_MVP_PLAN.md`](../experiments/E007-harness-mvp/DESKTOP_MVP_PLAN.md).

Run the core tests:

```bash
PYTHONPATH=desktop python3 -m unittest discover -s desktop/tests -v
```

Inspect the local library without printing text, paths or identifiers:

```bash
PYTHONPATH=desktop python3 -m pocket_i_core.library_cli inventory
```

Writing the private normalized library is a separate explicit action. The file
is created with mode `0600` and never overwritten:

```bash
PYTHONPATH=desktop python3 -m pocket_i_core.library_cli extract --output private-library.json
```

`HybridChatIndex` then routes one question to five whole conversations. It
combines BM25 word matching with a replaceable local embedding model and uses
the best matching message only to select the conversation; it does not send or
approve the message itself.

`build_cached_index` stores only hashed message keys, content hashes and float
vectors in a mode-0600 local SQLite file. It never stores conversation text or
paths. An unchanged second start reuses every vector; changed messages alone
are embedded again. A model-fingerprint change deliberately rebuilds the cache.

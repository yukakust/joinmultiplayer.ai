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

## First desktop shell

`app/` contains the Checkpoint 4A Electron shell and `pocket_i_app/bridge.py`
contains its bundled private sidecar boundary. The current window can inspect
the Codex-only Local Library and receives counts only. Asking the swarm remains
disabled until the evidence reader is connected.

Build the current native platform after installing the locked npm dependencies
and PyInstaller in the selected Python environment:

```bash
cd desktop/app
npm ci
POCKET_I_BUILD_PYTHON=/path/to/python ./build-current-platform.sh
```

Linux produces an unsigned development AppImage; macOS produces an unsigned
development DMG on a Mac. Signing and public distribution remain later release
steps.

The next physical macOS checkpoint uses the versioned
`site/experiments/E007/build-macos-alpha-v0.2.sh` helper. It builds in a new
temporary Downloads directory and copies the resulting DMG into Downloads. It
does not edit an existing checkout or remove an existing file.

Checkpoint 4B adds a minimal first-run setup screen and a pinned Qwen3-8B
Q4_K_M downloader. Downloads resume from a partial file and are promoted into
the private model directory only after exact size and SHA-256 verification.
The runtime and question path remain visibly disabled until the next
checkpoint.

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
the Codex and Claude Code Local Library and receives conversation counts only.
Asking the swarm remains disabled until the evidence reader is connected.

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

Checkpoint 4C applies the exact `forge-chassis-texture-v1` asset from the
Pocket i Figma file (node `19:2`) to that setup flow. The left display owns the
current action; the right display shows setup state. No model or privacy logic
changed in this visual checkpoint.

Checkpoint 4D removes setup copy that duplicated the small status display. The
main display now contains one instruction, one progress line and one action.
The question field stays absent until it can actually work.

Checkpoint 5A pins and verifies the official llama.cpp b10729 native runtime
during packaging. After the model and runtime are present, the main display
turns into a minimal local chat and sends one question to llama-cli through a
child-process pipe. Fixture inference and the packaged Linux runtime pass; a
real Qwen3-8B answer and physical macOS DMG still require owner inspection.

Checkpoint 5B labels the large download in plain language. The progress line
now names Qwen3 8B before showing transferred and total size.

Checkpoint 5C records the first physical Qwen3-8B answer on macOS. Inference
worked, but llama-cli's banner, prompt echo and exit text reached the chat. The
pinned-output adapter now extracts only the answer and disables runtime logs.

Checkpoint 5D physically verifies alpha.7 on the owner's MacBook. The existing
model was reused, Qwen3-8B answered locally, and the chat displayed only the
question and model answer. Local-memory retrieval and swarm transport remain
outside this checkpoint.

Checkpoint 6A adds the English layered identity module. A short kernel is
always present in companion chat; origin and reality capsules are selected only
for matching questions. Harness modules keep neutral task prompts. Physical
Qwen A/B inspection remains pending.

Checkpoint 6B physically compared the old neutral prompt with the layered
identity on five paired MacBook questions. Three identity answers passed, one
was partial, and the reality answer failed by calling the fictional Merger real.
The prompt-only design must not ship as alpha.8; invariant disclosures need an
application-level controller rather than model improvisation.

Checkpoint 6C accepts the owner's identity decision and tests the short kernel
on ten frozen Gate 15F evidence-to-answer cases. Both conditions preserve all
ten diagnoses, actions, and exact evidence-ID sets; the identity condition adds
no lore or unsupported fact. The run also exposed and fixed a long-prompt output
adapter fallback when pinned llama-cli abbreviates its echoed prompt.

Checkpoint 6D connects both accepted local sources to the desktop status panel.
The panel shows only `Codex N · Claude N`. Conversation text, paths, names,
identifiers and message coordinates remain inside the Python core and never
cross into the Electron renderer. Fixture tests cover both sources and the
counts-only boundary; a fresh packaged Mac scan remains the next physical gate.
The same bridge was also run directly on yukabox: it reported 61 Codex
conversations and no Claude Code library, while returning no private content.

Before Checkpoint 6E packaging, the count path was made metadata-only. It no
longer constructs conversations or reads message bodies merely to paint two
numbers. On yukabox the new inventory returned 68 Codex session records in
about a tenth of a second. The different number is expected: the earlier full
reader counted only non-empty visible conversations; the status panel counts
top-level session records. The pinned Mac build source is revision `c36e807`.

Checkpoint 7A supersedes the count-only package run with the first explicit
memory connection. The app shows `CONNECT MEMORY`, discloses the accepted Codex
and Claude boundary plus the 250 MB local search model, and does nothing until
the owner confirms. The bridge then reads visible messages, builds the real
cached MiniLM/BM25 index, and persists only hashes, vectors and count-only state.
The chat still uses base Qwen at this checkpoint; retrieval is connected next.

Checkpoint 7B connects the owner's question to that index. After consent, one
local memory process stays alive: it reads the allowed library once, keeps the
conversation text only in RAM, and reuses the same index for later questions.
The window shows five matching conversations and one short matched preview from
each. It does not ask Qwen to answer yet. Tests prove that two requests reuse one
process and that a second route reuses the same in-memory library and index.

The first physical Checkpoint 7C run failed honestly: after 65 minutes the
worker was still active, but the UI hit its fixed one-hour timeout and no final
state existed. Checkpoint 7D commits every 128 new vectors, reports saved-message
counts, removes the initial-build timeout, and lets the owner return to chat
while work continues. A forced-interruption test proves the next run reuses the
already committed batches.

Checkpoint 7E replaces the raw top-five debug screen with the first complete
local retrieval-to-answer path. Inside the app, the index still selects five
conversations, but it now keeps both a rare named anchor and a semantic message
from each. Bounded excerpts go to local Qwen3-8B, and the owner sees one short
answer with validated local source labels. This is not yet the full evidence
harness: exact-quote extraction, DeBERTa and outgoing-capsule approval remain
separate gates.

Checkpoint 7F puts an exact-evidence turnstile inside that same one-answer
path. Qwen first returns atomic claims plus copied source quotes. Ordinary code
rejects unknown labels, empty fields and any quote that is not an exact
substring of the selected local excerpt. Only surviving evidence reaches the
writer, and the final answer may cite only surviving evidence IDs. The NLI
stage is a replaceable local interface and reports `unavailable` when its
frozen model is absent; it never invents a decision. Packaging and validating
the accepted DeBERTa checkpoint is the next physical-build gate.

Checkpoint 7G rejects a broken INT8 export (`9/30` frozen decisions matched)
and accepts the native FP16 ONNX export (`30/30` matched). The build downloads
the 369,758,915-byte model and 8,648,864-byte tokenizer from the public lab,
verifies both SHA-256 hashes, and packages them as local resources. The sidecar
loads them lazily through ONNX Runtime. A physical Mac DMG run remains required.

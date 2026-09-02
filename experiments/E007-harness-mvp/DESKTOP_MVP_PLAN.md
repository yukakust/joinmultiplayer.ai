# Pocket i desktop MVP plan

Status: Checkpoint 0 accepted on 2026-08-31. No model training is authorised by
this checkpoint.

Progress: Checkpoint 1A fixed the portable core contract. Checkpoint 2A added
strict library adapters and passed a real Linux Codex inventory. macOS and
Windows physical adapter runs remain open.

Checkpoint 3A connected hybrid whole-chat routing. One opened real Linux query
found its anchor-defined chat at rank 1; a warm query took 0.201 seconds. The
318-second cold build failed the product latency requirement, so a private
persistent incremental index is mandatory before packaging.

Checkpoint 3B implemented that cache. A real unchanged restart reused all
2,926 vectors and loaded them in 0.238 seconds; an incremental catch-up embedded
only four new messages in 0.473 seconds. The cache is accepted as development
plumbing on Linux. Crash/concurrency and macOS/Windows remain unverified.

Checkpoint 4A created the first real desktop shell and a packaged Linux
AppImage. The window can inspect the Codex-only Local Library through a bundled
private Python sidecar. The renderer receives counts only. The 121 MB unsigned
development AppImage passed its packaged health check and found 58 conversations
and 2,948 visible messages on yukabox. The question field is deliberately
disabled: Qwen reading, approval and network exchange are not connected yet.

Checkpoint 4B added the first-run model step. The app checks memory and disk,
downloads a pinned 5.03 GB Qwen3-8B Q4_K_M file, resumes an interrupted partial
download and verifies exact size plus SHA-256 before installation. Three local
fixture tests cover success, resume and corruption rejection. The real 5.03 GB
download has not been run in this development checkpoint; llama.cpp and the
question path remain unconnected.

Checkpoint 4C replaced the temporary setup styling with the exact
`forge-chassis-texture-v1` PNG exported from the Pocket i Figma file. The main
display now owns the current setup action and the smaller display shows the
three states. This is a visual development checkpoint only; it does not advance
the runtime or inference claims.

Checkpoint 4D simplified the main display after owner review: symbol, one
instruction, progress and one button. Technical state remains on the smaller
display; unavailable future controls are not shown.

Checkpoint 5A adds the previously missing post-setup chat. The build downloads
and verifies a pinned official llama.cpp b10729 archive for its native target,
then embeds that runtime in the package. One-shot questions use a local process
pipe; no public or localhost inference server is opened. The current result is
plumbing-only until Qwen3-8B produces a real answer in a physical installation.

Checkpoint 5B records the first physical macOS setup observation: an anonymous
4.7 GB progress counter is not trustworthy enough. The next package names the
downloaded model directly on the same single status line.

Checkpoint 5C passed the first physical local-inference boundary: Qwen3-8B
answered on the owner's MacBook without a remote endpoint. It also exposed an
output-adapter failure: the chat displayed llama-cli diagnostics. The next
package removes the pinned runtime envelope and keeps only the generated answer.

Checkpoint 5D physically reran that boundary with alpha.7. The downloaded model
survived the application update, inference still worked, and the output adapter
showed only the user's question and Qwen's answer. This closes presentation of
one local answer, not memory, multi-turn context, or swarm behavior.

Checkpoint 6A implements personality as a separate English companion-chat
module. The always-loaded kernel stays below 130 whitespace-delimited words;
origin stays below 220 words with the kernel, and origin plus the honest reality
valve stays below 250. Neutral harness prompts never receive lore. The code boundary is tested
before any physical alpha.8 personality claim.

Checkpoint 6B failed the physical prompt-only A/B. Qwen preserved the single
ordinary reasoning control and handled brain disclosure and empty owner memory,
but it called the fictional Merger real. The failure remains public. A future
identity controller must own invariant facts outside generative output.

The owner accepted the 6B voice. Checkpoint 6C then passed the relevant work
regression: the short identity kernel was not worse than the original technical
writer on ten frozen physical Qwen3-8B evidence-to-answer pairs. A separate
runner-envelope bug exposed local paths in the private result only; it was not
published and the desktop output adapter gained a long-prompt regression test.

Checkpoint 6D exposes the first Local Library state in the app: conversation
counts for Codex and Claude Code. The renderer receives no conversation text,
path, title, identifier or coordinate. This is an interface and privacy-boundary
test, not yet a physical scan or evidence-retrieval result.
The unpackaged bridge smoke on yukabox found 61 Codex conversations and zero
Claude Code conversations. A packaged Mac scan remains unverified.

Checkpoint 6E changes status discovery to a metadata-only session inventory so
the UI does not parse gigabytes of message bodies merely to show counts. The
pinned alpha.8 Mac build at revision `c36e807` is awaiting the owner's physical
run. Evidence retrieval remains deliberately outside this gate.

The owner chose not to package another count-only build. Checkpoint 7A therefore
adds the explicit `CONNECT MEMORY` action first. Consent precedes any message
read; Codex and Claude visible messages build the accepted cached MiniLM/BM25
index. Only hashes, vectors and counts persist. Fixture coverage passes, while
the real FastEmbed download and Mac library build remain a future physical run.

Checkpoint 7B connects questions to the accepted index without pretending that
retrieval is already an answer. The app shows the five selected conversations
with short matched previews for owner inspection. A long-lived local sidecar
keeps allowed plaintext in RAM and prevents a multi-gigabyte source rescan on
every question. Public records contain synthetic examples and counts only.

Checkpoint 7C is the first physical package gate for that route. Builder v0.5
pins revision `ca5bbde`, installs the locked FastEmbed dependency before
PyInstaller, runs both suites, and produces a revision-labelled DMG without
overwriting older evidence. The owner tests one real question; previews stay
private and only a redacted outcome may be published.

Checkpoint 7C failed physically after the active worker crossed the fixed
one-hour UI timeout. Checkpoint 7D replaces the all-or-nothing embedding pass
with committed 128-message batches, visible counts, no initial-build timeout,
and a background path back to chat. Restart reuse is a required pass condition.

Checkpoint 7E removes raw retrieval cards from the owner path. The internal
route selects chats, preserves a rare named anchor plus semantic context, and
asks local Qwen3-8B for one cited answer. Invalid source labels fail closed.
Exact quote extraction and DeBERTa remain the next internal acceptance layer;
the development result must not be described as the complete harness.

## What we are building

One desktop application with the same harness on macOS, Windows and Linux.
The phone is outside the MVP. The application downloads a selected model
preset after installation; models are not bundled into the installer.

The MVP answers one kind of request:

> I already asked my own AI and still do not know how to solve this. Ask the
> network of pocket i for useful knowledge with evidence.

## One source tree, three packages

The proposed packaging shape is:

```text
Tauri desktop window
        ↓ local process channel; no open localhost server
one Python harness core
        ↓
native llama.cpp runtime + downloaded model preset
```

The UI and core remain the same. A native build matrix supplies only the
platform-specific shell, Python sidecar and llama.cpp runtime:

- macOS: signed `.app` inside a `.dmg`;
- Windows: signed `.exe` / `.msi`;
- Linux: `.AppImage`, with `.deb` later if needed.

Model weights are downloaded after installation, so installers stay small and
the user can change presets without reinstalling the application. Native CI
runners must test each package; cross-compiling one untested binary is not an
MVP release.

## The seven checkpoints

### 1. One local core

Turn the accepted E007 modules into one command that accepts a question and
produces one inspectable trace. The core must run identically on all three
desktop operating systems.

### 2. Local Library

Read only visible user and assistant messages from Codex, Claude Code and the
locally available ChatGPT history. Unknown formats fail closed. Tool calls,
thinking, terminal output and arbitrary files stay outside the library.

### 3. Find and prepare evidence

Route the question to five whole conversations. Read conversations up to
10,000 model tokens whole; search inside longer conversations without cutting
messages. The harness numbers immutable evidence blocks. Qwen proposes useful
claims and selects only block IDs; ordinary code copies the exact source text
behind those IDs. One claim may keep several blocks and sources when the whole
set is needed. Qwen never has to retype a quote. DeBERTa remains a cautious
signal, not the sole judge.

### 4. Safe network exchange

Each installation gets a local identity. A pocket i sends only a small evidence
capsule after secret scanning and an owner-visible preview. Empty replies are
counted. Raw conversations never leave the device.

### 5. Assemble the answer

Keep the best-supported version and all competing versions on separate shelves.
Qwen3-1.7B may restate accepted evidence as a human answer but may not invent a
missing fact. Every sentence remains traceable to a device, conversation and
exact source span.

### 6. One simple desktop UI

The owner can install a preset, see library status, ask the network, approve
outgoing capsules, read the answer, open every source step and see recorded
weaknesses. The interface must use plain language.

The Checkpoint 4A shell implements only the first of these actions: viewing the
Codex library status. It is a package checkpoint, not the finished UI.

### 7. Three builds and one locked test

Build a macOS app, Windows executable and Linux application from the same core.
Run a fresh English-only end-to-end test on at least two physical computers.
Publish every question, redacted trace, answer, failure and human audit.

## Model presets for the first app

The packaging must support presets rather than model-specific harness code.
The first validated path may download Qwen3-8B for evidence reading and
Qwen3-1.7B for final writing. A smaller preset can be exposed as experimental,
but it must not inherit the larger preset's quality claims.

## Definition of MVP done

The MVP is done only when a new user can:

1. install the app on one supported desktop OS;
2. download a model preset without using a terminal;
3. build a local library without leaking hidden logs or arbitrary files;
4. ask another physical pocket i one English question;
5. inspect and approve exactly what leaves each device;
6. receive an answer with evidence and separate alternative versions; and
7. reproduce the same flow from installers on macOS, Windows and Linux.

## Explicitly later

- phone builds;
- autonomous sending without owner approval;
- model training or personal weight updates;
- multilingual quality claims;
- arbitrary user-selected folders;
- claims that the current harness is a complete distributed neural network.

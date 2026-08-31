# Pocket i desktop MVP plan

Status: Checkpoint 0 accepted on 2026-08-31. No model training is authorised by
this checkpoint.

Progress: Checkpoint 1A fixed the portable core contract. Checkpoint 2A added
strict library adapters and passed a real Linux Codex inventory. macOS and
Windows physical adapter runs remain open.

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
messages. Qwen proposes useful claims and exact message coordinates. Ordinary
code verifies that every quoted span really exists. DeBERTa remains a cautious
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

# Pocket i desktop — developer handoff

## What we are building

Pocket i is a desktop app that searches the owner's local Codex and Claude Code
conversations, finds evidence for a question, checks that evidence, and writes a
short cited answer. The long-term goal is a network of personal AIs that can
share useful, consented knowledge without becoming one central model.

## Current checkpoint

- Branch: `agent/game-loop-v0.1`
- App: `desktop/app`, version `0.1.0-alpha.27`
- Core/index: `desktop/pocket_i_core`
- Public experiment record: `site/experiments/E007`
- Current Miro frame: `E007 · CURRENT HARNESS · alpha.26 · 2026-09-04`
- macOS builder: `site/experiments/E007/build-macos-alpha-v0.25.sh`

The Mac keeps conversation discovery, the index, exact evidence restoration,
DeBERTa, secret scanning, and private audit logs. Qwen3-Reranker-4B and
Qwen3-8B currently run on Yuka's private yukabox through Tailscale.

## Current answer path

1. Local hybrid search chooses five likely conversations.
2. Short chats stay whole; long chats contribute complete turns/messages.
3. The remote reranker marks each candidate `TAKE`, `NOT_SURE`, or `DROP`.
4. Qwen3-8B selects useful messages and extracts small claims with line handles.
5. Local code restores exact source lines and rejects invented handles.
6. Local DeBERTa checks claim-to-source support; the secret scanner can stop it.
7. Qwen checks question relevance; omitted or `unrelated` claims are dropped.
8. DeBERTa separates agreeing and conflicting versions into piles.
9. Qwen writes only from the verified “used” shelf and cites `[E1]`, `[E2]`.

## Privacy contract

The server path is selected by default so users do not download large models,
but it is not silently enabled. On first launch the owner must accept a clear
warning that their question and selected Codex/Claude excerpts leave the device.
Without consent, the Electron main process blocks both ordinary and memory
inference. Consent is local, revocable, and bound to the exact endpoints.
Private questions, excerpts, paths, identifiers, and audit logs must never be
committed or published.

## Verify changes

```bash
PYTHONPATH=desktop python3 -m unittest discover -s desktop/tests -p 'test_*.py'
npm --prefix desktop/app test
```

Expected at this checkpoint: `39/39` Python tests and `46/46` desktop tests.

## Next checkpoint

Build alpha.27 on the owner's Mac and physically verify: brain selection does not start work, `WAKE` starts only the selected mode, `OPEN TEST LOGS` opens the private audit directory, first-run warning,
consent, yukabox health, one memory-backed answer, private audit creation, and
disconnect. Only then give the DMG to Vitalik. Vitalik must have Tailscale
access. This alpha does not yet provide public authentication, tenant isolation,
or a production SLA for the shared server.

Preserve old diagrams, failed runs, and public artifacts: they are part of the
experiment history rather than cleanup targets.

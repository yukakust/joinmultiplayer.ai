# Pocket i desktop — developer handoff

For the overall vision and contribution tracks, read [START_HERE.md](../START_HERE.md).

Reviewed against `main` at `cb7a35b` on 9 September 2026.

## What we are building

Pocket i is a desktop app that searches the owner's local Codex and Claude Code
conversations, finds evidence for a question, checks that evidence, and writes a
short cited answer. The long-term goal is a network of personal AIs that can
share useful, consented knowledge without becoming one central model.

## Current checkpoint

- Development baseline reviewed here: `main` (older branch instructions are historical)
- App: `desktop/app`, version `0.1.0-alpha.35`
- Core/index: `desktop/pocket_i_core`
- Public experiment record: `site/experiments/E007`
- Historical Miro frame (not verified against alpha.35): `E007 · CURRENT HARNESS · alpha.26 · 2026-09-04`
- macOS builder: `site/experiments/E007/build-macos-alpha-v0.25.sh`

The Mac keeps conversation discovery, the index, exact evidence restoration,
DeBERTa, secret scanning, and private audit logs. Qwen3-Reranker-4B and
Qwen3-8B currently run on Yuka's private yukabox behind the authenticated
`brain.joinmultiplayer.ai` HTTPS gateway.

## Current answer path

1. Local hybrid search chooses five likely conversations.
2. Chats within a conservative 20,000-byte input budget stay whole; longer
   chats contribute complete turns, and an oversized turn contributes selected
   whole paragraphs with derived source coordinates.
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

These are the test entry points. Historical test counts are not a current pass guarantee; run the suites on your chosen revision.

## Known limits and next verification

The secret scanner currently checks retained claims after early remote calls;
it does not prevent all secrets in the original question or context from leaving
the device. Final citation validation does not prove every final assertion.

Verify the current package on a Mac: consent and revocation, authenticated
inference access, memory setup, one supported answer, one honest refusal,
oversized conversations, private audit creation, and disconnect/recovery.
The alpha.35 input-budget fix needs packaged regression coverage, not merely a
version bump. The HTTPS gateway supersedes the older Tailscale-only client setup;
obtain current access instructions privately from Yuka. Authentication alone is
not evidence of tenant isolation or a production SLA.

Preserve old diagrams, failed runs, and public artifacts: they are part of the
experiment history rather than cleanup targets.

# Pocket i harness v0.2 — accepted path

Status: architecture checkpoint after E007 Gate 3C.6Q. Some blocks exist only
as tested parts. This is not yet a downloadable end-to-end product.

## The path

1. Install one modular Pocket i app and choose a model preset.
2. Keep the person's exact question and its hash.
3. Ask likely pocket i in parallel using public capability cards.
4. Each pocket i searches only memory its owner allowed.
5. Every contact ends as `found`, `empty`, `blocked`, `error`, or relay-created
   `offline`.
6. Before sending, a security module enforces permission and removes secrets.
7. Send a readable capsule: one claim, exact evidence, source location,
   lineage, conditions, limits, and permission.
8. Prefer recall at the sender: an uncertain useful piece may travel; losing it
   cannot be repaired later.
9. The receiver checks relevance with Qwen3-Reranker-4B Q4:
   `TAKE / NOT SURE / DROP`.
10. Ordinary code proves that the exact passage came from the named source
    snapshot and byte range.
11. DeBERTa NLI checks only `exact passage + one atomic claim`:
    `SUPPORTED / CONTRADICTED / NOT PROVEN`. The user question stays outside.
12. Keep each pocket i's knowledge as a chain: one current head plus preserved
    history. Check truth, applicability, and independence later, after all
    candidate answers arrive.
13. Merge only answers that make the same claim. Evidence, lineage, and a
    supported minority must remain visible.
14. Pinned Qwen3-1.7B writes the final answer using only accepted piles. It does
    not invent missing pieces. Empty input bypasses the model and returns a
    fixed response.
15. The harness records `contacted → found → accepted → used → improved` so it
    learns value, not popularity.

## What Gate 3C.6P–Q taught us

The same NLI model scored `20/20` when it saw one exact source sentence and one
small claim. It scored `15/20` when we also mixed in the user's question and
surrounding document text. A human checked every gold label and all five new
errors.

So the accepted interface is deliberately narrow:

```text
exact verified source passage + one atomic claim
→ DeBERTa-v3-base NLI
→ SUPPORTED / CONTRADICTED / NOT PROVEN
```

This does not prove that the source is true, current, independent, applicable,
or safe to share. Those are different jobs for different modules.

## Evidence boundary

This is synthetic English development evidence reviewed by one researcher.
It still needs an independent held-out set, other languages, quantized-device
tests, and an end-to-end run on real pocket i devices.

## What Gate 12A taught us

The narrow chain mechanism is accepted. It found the current head and kept the
old records in 10/10 frozen synthetic cases. One three-record chain also moved
from yukabox to miracle-prod with the same SHA-256. This proves transport and
history mechanics only; it does not prove truth or applicability.

## What failed in Gate 13A

A frozen multilingual MiniLM embedding model tried to merge 21 English and
Russian answers. It recovered 0/6 paraphrase groups exactly, reached pairwise
F1 0.395062, and made 4/5 forbidden merges. It grouped answers about the same
topic even when they made different or opposing claims.

Therefore embeddings may find candidates, but they may not make the final
merge decision. This failed result is part of the public experiment history.

## What Gate 13B taught us

DeBERTa compared the 14 already opened English answers in both directions. Two
answers entered one pile only if each entailed the other. It recovered 4/6
paraphrase piles, made zero forbidden merges, lost no answers, and reached
pairwise F1 0.8. Two valid paraphrase pairs stayed separate.

This is safer than the embedding baseline, but it did not pass. DeBERTa also
called 19 unrelated pairs contradictions. Because this set had no separately
labelled true-conflict exam, the harness must not display those edges as real
disputes. Gate 13 remains open.

## What failed in Gate 13C

A second pass showed DeBERTa two complete piles and asked whether they express
the same claim. It recovered both missed pairs, but approved 42 false merges,
returned entailment for 44/45 pairs, and collapsed all answers into one group.

This checkpoint was trained for literal premise-to-hypothesis inference, not
meta-statements about groups. Do not add the Gate 13C second pass to the
accepted harness.

## Accepted Gate 13D architecture

The owner accepted this pipeline for harness v0.2 on 2026-08-29:

1. DeBERTa builds cautious piles from mutually supporting original answers.
2. Qwen3-0.6B rewrites each pile as one short readable claim.
3. DeBERTa checks that claim against every original in both directions. If it
   fails, the Qwen rewrite is discarded and the original pile remains.
4. Only validated claims are compared in both directions to form final piles.

Original answers, evidence, sources, and lineage are never replaced by the Qwen
summary. Separate versions remain visible. The locked synthetic development run
improved 4/6 piles to 5/6 with zero false merges and validated 9/10 rewrites.
The owner considered the lost word `exclusively` acceptable in that specific
affirmative instruction; this does not make the loss safe in every domain. The
recovered merge also depended on a near tie: entailment 0.505623 versus neutral
0.493628. The architecture is accepted for the MVP, while its reliability at
scale and across domains remains unproven. Decision record:
`/experiments/E007/answer-piles-accepted-architecture-v0.1.json`.

## Locked Gate 14A: write only what the swarm supplied

Ten English synthetic cases are frozen before Qwen's first run. Eight provide
accepted piles; two are empty. Qwen may make the supplied claims readable, but
may not add facts, conclusions, advice, or invented statements about missing
knowledge. Different versions must stay visible as different versions. Empty
input bypasses Qwen and returns one fixed response.

The result passes only if all ten cases preserve every supplied meaning, add no
new factual meaning, keep numbers/negation/uncertainty/conditions, return both
empty cases exactly, and avoid truncation. Manual review is authoritative;
DeBERTa is diagnostic. Protocol:
`/experiments/E007/answer-synthesis-protocol-v0.1.json`; cases:
`/experiments/E007/answer-synthesis-world-v0.1.json`; UI:
`/experiment/e007/gate-14a/`.

The run produced every requested output and no truncation, but manual review
passed only 8/10. Qwen invented no new factual claim. It did, however, remove
the explicit separate-version framing in one case and completely omit one
supplied pile in another. Gate 14A failed. Free-form multi-pile synthesis is not
accepted. The next candidate gives Qwen one pile at a time and lets ordinary
code preserve pile order and version labels. Result:
`/experiments/E007/answer-synthesis-result-v0.1.json`; audit:
`/experiments/E007/answer-synthesis-human-audit-v0.1.json`.

Gate 14A.2 repeats the exact ten-case test with Qwen3-1.7B. Inputs, prompt,
decoding, empty-input response, and manual rubric remain frozen; only model size
changes. The paired test asks whether a larger allowed model can beat the 0.6B
score of 8/10 without inventing more facts. Protocol:
`/experiments/E007/answer-synthesis-qwen17b-protocol-v0.1.json`.

Qwen3-1.7B passed all 10/10 cases under the same manual rubric. It restored the
two-version framing in S02, kept the second pile in S08, and added no factual
claim. There were no truncations and both empty responses were exact. This
supports a larger model preset for final synthesis. It does not yet show that
1.7B improves routing, local retrieval, NLI acceptance, history, or pile
formation; those modules must be replayed separately. Result:
`/experiments/E007/answer-synthesis-qwen17b-result-v0.1.json`; audit:
`/experiments/E007/answer-synthesis-qwen17b-human-audit-v0.1.json`.

The owner accepted Gate 14 for harness v0.2 with pinned Qwen3-1.7B on
2026-08-29. Free-form multi-pile synthesis on 0.6B is not accepted. This is an
MVP architecture decision supported by paired synthetic English development
evidence, not an end-to-end or phone result. Decision:
`/experiments/E007/answer-synthesis-accepted-architecture-v0.1.json`.

## Still missing before the first MVP

1. One installable app with pinned presets and uninstall/update.
2. Real-phone runtime measurements for quantized 1.7B and the 4B reranker.
3. Allowlisted local-library adapters plus a privacy-safe capability card.
4. One integrated run across all accepted modules rather than separate scripts.
5. An authenticated MacBook + yukabox + phone room with complete receipts.
6. A locked end-to-end test and one simple public inspection UI.

## Gate 16B.0 — local library discovery

The first real-memory step deliberately stops before parsing or segmentation.
A read-only probe looks only in the app-owned storage of Codex, Claude Code,
and ChatGPT desktop. It may report paths, formats, counts, sizes, and permission
errors. It may not print conversation text, create an index, contact a server,
or modify a source file. The owner must review the MacBook inventory before the
next step. Finding a ChatGPT app database does not prove that every cloud chat
is cached locally.

The yukabox inventory established the first local-library law for the MVP:
**an app folder is not a library**. Codex had 115 likely session files, but its
root also contained authentication, caches, logs, plugins, attachments, queues,
and temporary state. Each source adapter must therefore use a strict allowlist;
everything else is denied by default. Discovery never grants permission to
parse, index, or share a file.

Gate 16B.1 then counted only visible user and assistant messages. It found 115
session files but only 103 unique session IDs: 64 main conversations and 39
child-agent conversations. Deduplication removed 939 repeated message records
with zero ID/content conflicts. Main conversations contain a median 1,927
Qwen3 tokens; two exceed 100k. The exact private text and chat titles remain
unpublished. No topic grouping, secret scan, or search ran.

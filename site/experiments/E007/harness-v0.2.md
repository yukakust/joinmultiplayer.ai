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
11. DeBERTa NLI checks `verified exact quote + bounded neighbouring source
    context + one atomic claim`: `SUPPORTED / CONTRADICTED / NOT PROVEN`. The
    user question stays outside.
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

The first accepted interface was deliberately narrow:

```text
exact verified source passage + one atomic claim
→ DeBERTa-v3-base NLI
→ SUPPORTED / CONTRADICTED / NOT PROVEN
```

This does not prove that the source is true, current, independent, applicable,
or safe to share. Those are different jobs for different modules.

Gate 16D.11 later isolated source-only context on real Codex messages. The exact
quote stayed marked and byte-verified, the person's question stayed outside,
and only neighbouring text from the same message was added. On 18 opened
English cases, contextual DeBERTa accepted 16/16 supported claims and 0/2
unsupported claims after one old human label was corrected. This makes the
bounded source window the working MVP candidate, but a fresh locked replication
is still required before production acceptance. Results:
`/experiment/e007/gate-16d/deberta-context/`.

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

### Desktop integration checkpoint 7M

The alpha.13 ten-question physical regression exposed an integration error,
not a new model result: DeBERTa's `neutral` label was logged but every exact-ID
candidate still reached the writer. The absent named-model controls therefore
became cited invented answers.

Pocket i 0.1.0-alpha.14 now wires the accepted Gate 13D sandwich into the local
answer path:

```text
exact evidence IDs
→ source entails claim (DeBERTa)
→ cautious mutual-entailment piles
→ readable Qwen canonical claim
→ every original ↔ canonical (DeBERTa)
→ final mutual-entailment piles
→ grounded writer
```

`neutral`, `contradiction`, and `unavailable` claims stop before the writer. A
bad Qwen canonicalization is discarded without deleting its exact originals.
This code checkpoint passes deterministic tests for a supported answer, an
adjacent-memory hallucination, a conflicting supported version, and a broken
canonical rewrite. It remains unverified on the owner's physical memory until
the unchanged alpha.14 DMG repeats the ten-question regression. Public record:
`/experiments/E007/desktop-full-harness-checkpoint7m-v0.1.json`.

### Desktop correction checkpoint 7N

The owner's alpha.14 run exposed a second integration mismatch. The strict gate
worked — unsupported inventions stopped — but the desktop gave DeBERTa only the
selected short evidence blocks. That was the older quote-only interface, whose
low recall had already been measured in Gate 16D.9. Several supported answers
therefore stopped too.

Alpha.15 implements the already accepted Step 11 interface rather than changing
the architecture:

```text
immutable exact quote
+ bounded neighbouring text from the same selected source
+ one atomic extracted claim
→ DeBERTa
```

The person's question is not added to the NLI premise. Ordinary code first
proves that every quote is still an exact substring of the source excerpt, then
builds a source-only window centred on that quote. If the exact evidence and
claim cannot fit, the candidate fails closed. Claim-to-claim pile comparisons
remain separate and use the accepted Gate 13D sandwich.

This is an implementation checkpoint. It does not turn the earlier alpha.14
physical failure into a pass; the owner must repeat the visible questions in a
new build. The exact code-to-harness map is published in
`/experiments/E007/desktop-harness-crosswalk-checkpoint7n-v0.1.json`.

### Desktop diagnostic checkpoint 7O

Alpha.15 improved the owner's physical regression from two to four supported
answers out of eight and correctly blocked both absent-answer controls. The
remaining four false negatives could not be located because each question
overwrote the previous private test log. Alpha.16 preserves every completed or
failed question as a separate owner-only JSON file and keeps the existing
last-log file only as a convenience copy. The app opens the containing folder;
it never uploads these logs. The failed answers must now be repeated before any
grounding rule changes.

The first alpha.16 DMG failed at startup: Electron's explicit package allowlist
did not include the new audit module. Alpha.17 corrects the allowlist and adds a
packaging regression test. No model result came from the broken build.

### Retrieval diagnostic checkpoint 7P

The first durable alpha.17 log located one false negative before Qwen's claim
extraction: the `/x` question received ten unrelated excerpts. The current
desktop tokenizer had reduced `/x` to `x`, and the current reader always exposed
two messages per selected chat rather than the accepted short-chat/long-chat
procedure. No grounding change is justified by this trace.

Before another DMG, a private local A/B freezes the four false-negative
questions and compares the unchanged BM25+MiniLM route with one exact-anchor
candidate. The candidate preserves routes, model/version names and numbers
such as `/x`, `DeBERTa-v3`, and `499`. Qwen and DeBERTa do not participate. The
owner inspects both columns locally; no conversation excerpt is uploaded.
Protocol: `/experiments/E007/anchor-search-ab-protocol-v0.1.json`.

The follow-up private-library development test adds corpus-derived rare
two- and three-word phrases without a domain vocabulary. It recovered the
needed evidence for all four frozen questions, versus three of four for the
technical-anchor route alone. Because the phrase route also demoted two
already-correct results, it is accepted only as an additive fallback: preserve
the technical-anchor order and add the first novel phrase-derived conversation.
Public, privacy-safe result:
`/experiments/E007/phrase-search-ab-result-v0.1.json`.

The subsequent 30-question full-pipeline run rejected that tentative fallback
decision. The extra phrase-derived conversation was selected three times: one
useful claim was rejected by DeBERTa, one irrelevant claim was rejected, and
one irrelevant but source-grounded claim reached the final answer. All ten
absent-answer traps were safely refused, but the fallback recovered zero final
answers. Therefore phrase fallback is **not accepted for the desktop app**;
the technical-anchor result remains 3/4. Result:
`/experiments/E007/phrase-fallback-30-result-v0.1.json`.

### Checkpoint 7S.1 — question-to-claim relevance

Checkpoint 7R exposed a missing bridge. DeBERTa can establish that an exact
source passage supports one atomic claim, but that does not establish that the
claim helps answer the owner's question. The new gate receives only the exact
question and already-grounded claims. It must label every claim `ANSWERS`,
`CONTRIBUTES`, or `UNRELATED`; code keeps the first two and drops the third.
Missing, duplicate, invented, or malformed decisions fail closed.

The first replay is deliberately isolated: it reuses the private grounded
claims from the frozen 30-question checkpoint and does not rerun retrieval or
writing. Human review is authoritative. Protocol:
`/experiments/E007/question-claim-relevance-protocol-v0.1.json`.

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

### Checkpoint 7S.2 — executable Miro order

The previous desktop candidate accidentally let Qwen write a claim before the
accepted raw-passage reranker. The late 7S.1 question-to-claim check could not
repair this: all eight already grounded claims looked answer-shaped to Qwen.
That ordering is rejected and remains part of the experiment history.

The executable order is now frozen in
`/experiments/E007/miro-executable-harness-v0.1.json`:

```text
unchanged question
→ frozen raw retrieval candidates
→ security boundary
→ Qwen3-Reranker-4B on question ↔ raw excerpt
→ Qwen3-8B extracts atomic claims and selects existing evidence IDs
→ ordinary code resolves exact evidence
→ DeBERTa checks source ↔ claim
→ evidence shelves
→ Qwen3-8B writes only from accepted shelves
→ ordinary code checks final citations
```

Qwen must not see a raw excerpt that the reranker marked `DROP`. The focused
private replay protocol is frozen before inference at
`/experiments/E007/raw-first-reranker-replay-protocol-v0.1.json`. It reuses the
same eight already opened cases and therefore cannot establish unseen
generalization or retrieval recall.

The private replay completed on 2026-09-03 and failed its full gate. The
reranker forwarded all five useful cases and dropped none, but stopped only one
of three wrong-context cases. The other two continued as `NOT_SURE`. Qwen3-8B
then produced two correct final answers out of eight and one wrong answer from
an irrelevant but internally supported excerpt. Exact-ID validation accepted
no invented IDs, and no DeBERTa non-entailment reached the writer.

Decision: keep the raw reranker before Qwen, but do not put this candidate into
the desktop app. `NOT_SURE` needs its own path, and the extraction task after
reranking still needs simplification. Public aggregate:
`/experiments/E007/raw-first-reranker-replay-result-v0.1.json`.

### Checkpoint 7S.3 — minimal exact evidence

The next private development replay kept the same eight opened cases but split
the frozen source bundles into 118 exact sentences. Qwen3-Reranker-4B was asked
to select citable evidence before Qwen3-8B could extract a claim. Qwen could
read the complete source for context, but ordinary code allowed it to cite at
most two sentence IDs marked `TAKE`.

This strict policy failed on recall. It admitted no sentence from any of the
three wrong-context cases, and both answers it produced were correct. However,
it admitted evidence for only two of five useful cases; 47 sentences remained
`NOT_SURE` and were unavailable to Qwen. The separation between readable
context and citable evidence remains promising, but `TAKE`-only sentence
selection is rejected. Public aggregate:
`/experiments/E007/minimal-evidence-selection-result-v0.1.json`.
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
## Checkpoint 7T.2 — whole turns accepted for the playable MVP

The corrected run removed the rejected sentence and character slicing. It
routed the unchanged question to five conversations, passed a whole short
conversation or complete conversational turns through Qwen3-Reranker-4B, let
Qwen3-8B return an atomic claim with an exact message quote, verified that
quote with ordinary code, checked source support with DeBERTa, scanned the
outbound capsule for secrets, and returned `FOUND`, `EMPTY`, or `BLOCKED`.

## Checkpoint 7U — remote brain requires explicit consent

The shared yukabox reader and reranker are now the default execution path, so a
fresh installation does not download model weights. Default selection is not
silent consent: before the first remote request, the owner sees that their question and selected
Codex or Claude excerpts will leave the computer and be processed on Yuka's
private yukabox through Tailscale. The warning says not to use this alpha mode
for secrets. Only an explicit **I UNDERSTAND · CONNECT** action stores consent.

The main process rejects both ordinary and memory-backed inference while the
switch is off, so hiding or bypassing the renderer cannot silently send text.
Consent is local, revocable, and bound to the configured reader and reranker
URLs; an endpoint change invalidates it. This checkpoint does not claim user
authentication, tenant isolation, or readiness beyond a trusted Tailscale test.
The private audit writes the exact pre-reranker inputs before the network call
and then records successful completion of all reranker decisions. These fields
remain owner-private; the public record contains only aggregate outcomes.

Human review scored the eight synthetic English development cases as 6 fully
correct, 1 partial, and 1 wrong. The partial answer explained why `Llama-3.3`
was split but omitted the requested remedy. The wrong answer returned a true
watering fact even though the question asked for a missing temperature. The
owner accepts this path for the first playable build with both weaknesses
visible as future Pocket i upgrades. This remains development evidence, not a
locked or generalization result. Decision:
`/experiments/E007/outbound-whole-turn-pilot-owner-decision-v0.1.json`.

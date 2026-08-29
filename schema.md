# Pocket i harness — agreed path

Status: working architecture agreement after E007 Gate 3C.6Q. This is not a
claim that every module already exists or has passed a physical-device test.

E007 Gate 3C.6A.2 adds one development finding about local source retrieval:
do not cut memory into isolated equal-size word blocks. Preserve document
structure and overlapping neighbour context, then keep exact source ranges.
This improved complete retrieval from 6/10 to 9/10 and required-atom recall
from 9/14 to 14/14 in one synthetic English manual. It is not accepted as a
finished cutter: one neighbouring opposite rule for Aster-8 also survived an
Aster-9 query, so a later condition/entity check is still required.

E007 Gate 3C.6B accepts the four-part incoming capsule as a development-level
message contract: sender claim, exact source window up to 500 Qwen tokens,
exact sender-highlighted subrange, and versioned source locator with byte
coordinates. Ordinary code validates bytes before inference. The Q4 relevance
module sees only question + complete source window; sender claim and highlight
remain hidden. In one frozen synthetic English set it kept 8/8 useful windows,
took 0/8 misleading windows, and the mechanical gate rejected all 8 broken
packets. Claim support now has one accepted development-level module. Source
truth, privacy, applicability, and independence are not yet accepted modules.

## The whole path

```text
Person writes one question
        ↓
Harness keeps the exact text
        ↓
Speculative Attention asks likely pocket i
        ↓
Every contacted pocket i either replies or reaches the relay deadline
        ↓
Each pocket i searches only permitted local memory
        ↓
found → send a safe knowledge capsule immediately
empty → send an empty receipt
blocked → report that something was found but cannot be shared
error → report that the search failed
offline → the relay records that no reply arrived
        ↓
Harness checks evidence, conditions, privacy, and source lineage
        ↓
Similar claims collapse into one claim, but their evidence stays visible
        ↓
Harness preserves disagreements and supported minority views
        ↓
Only then does a model assemble the answer for the person
```

## 1. Exact question

The person presses **Ask the pocket i network**. The harness keeps the exact
question. It does not silently rewrite the question or force the person to fill
in a JSON form.

Every recipient gets the same question hash. That lets us prove that all pocket
i were asked the same thing.

## 2. Speculative Attention

The harness compares the whole question with short public capability cards. A
card says what a pocket i may know; it does not expose private memory.

Attention answers only: **where should we look first?** Its score is a ranking
signal, not a probability, proof, or measure of truth.

For small experiments, a cheap beacon may be sent to every pocket i. This gives
us ground truth about which cards the router would otherwise miss.

## 3. Local search

A pocket i never searches the whole device by default. Its owner explicitly
chooses which collections may be indexed and which may be shared automatically.

The exact question enters the device. Search happens locally. The full memory
does not leave the device.

A found fragment is only a **candidate**. One pocket i cannot know whether its
piece will improve the final answer because it cannot see the whole puzzle.

## 4. Every contact gets a visible outcome

Silence is not the same as finding nothing. An online pocket i returns one of
the first four states. If it does not answer before the deadline, the relay—not
the device—creates the fifth state:

| State | Meaning |
| --- | --- |
| `found` | A permitted candidate was found and a capsule was sent. |
| `empty` | Search completed honestly and found nothing useful enough to send. |
| `blocked` | A candidate exists, but policy does not allow sending it. |
| `error` | The pocket i received the question but could not finish. |
| `offline` | The relay created this state because no response arrived before the deadline. |

This lets the harness count how many pocket i were contacted, answered, found
something, were blocked, failed, or stayed offline.

## 5. Knowledge capsule

A `found` response sends a small human-readable capsule immediately, but only
from memory that is allowed to leave the device.

```json
{
  "status": "found",
  "claim": "Image tiling may help detect small objects.",
  "evidence": "For 8–16 pixel objects, recall increased from 0.31 to 0.47 after tiling.",
  "source": "local experiment, 2026-05",
  "source_lineage": "exp-cv-017",
  "conditions": "4K images, labelled small objects, 20% overlap",
  "limitations": "Tested on one dataset",
  "permission": "share_this_capsule"
}
```

The JSON is packaging. The content must remain understandable to a person.

A capsule contains:

- `claim` — one clear statement;
- `evidence` — the observation, exact excerpt, measurement, experiment, or
  other support;
- `source` — what kind of source produced the evidence;
- `source_lineage` — which responses ultimately come from the same origin;
- `conditions` — where the claim may apply;
- `limitations` — what the capsule does not establish;
- `permission` — what the owner allowed the network to receive.

If there is no evidence, the claim may still be sent, but it must be labelled as
a `hypothesis` or `opinion`, never as a verified fact.

## 6. Evidence before popularity

Similar claims may collapse into one readable group. Their evidence must not be
discarded.

Ten copies of the same article are one lineage, not ten independent minds. Ten
independent experiments may be ten separate supports. The harness records both
the number of messages and the number of independent lineages.

The result should be readable like this:

```text
Claim: Image tiling helps detect small objects.

37 matching messages
8 independent sources
3 experiments
1 study

Best evidence: ...
Conditions: ...
Supported alternative: ...
```

The harness must preserve a supported minority view even when most messages say
something else.

## 7. Two different measures of value

`candidate_match` means a pocket i believed its fragment was worth offering.

`realized_value` means later checks showed that the fragment was accepted, used,
and improved the final answer or decision.

The network should learn from realized value, not from message volume or a
pocket i's confidence alone.

Useful funnel metrics are:

```text
contacted
→ delivered
→ found / empty / blocked / error / offline
→ capsules accepted
→ capsules used
→ answers improved
```

## Honest boundary

E007 Checkpoint 3A demonstrated exact-question delivery and public-card ranking
for four processes on two physical devices. Checkpoint 3B then demonstrated
physical local search, terminal receipts, a blocked synthetic private record,
and exact transport of stored evidence capsules. It did not find one method
that both rejects noise well and retrieves every needed source.

The locked protocol is `site/experiments/E007/local-offer-protocol-v0.1.json`;
the scored result is `site/experiments/E007/local-offer-result-L0001.json`.
Checkpoint 3B still does not test extraction from messy personal memory,
validation, deduplication, merging, a final answer, or scale.

Checkpoints 3C.2 and 3C.3 showed that free-form Qwen3-0.6B is not a reliable
meaning judge for accepting incoming capsules. Gate 3C.4 then compared special
relevance scorers. Qwen3-Reranker-0.6B lost no useful source but was too often
unsure. Gate 3C.5 tested one stronger scorer: Qwen3-Reranker-4B and its Q4/Q5
copies made the same 24 decisions; Q4 kept 8/8 useful pieces and is 2.50 GB.
The Q4 process peaked at 4.57 GB RAM on yukabox with one question at a time and
a 512-token context. That is not yet a phone result.

So the current candidate acceptance step is modular and simple:

```text
question + one offered memory piece
→ Qwen3-Reranker-4B Q4
→ TAKE / NOT SURE / DROP
```

`NOT SURE` is not silently discarded. It remains available for a later module.
This scorer judges relevance only. It does not prove that a claim is true, safe
to disclose, independent, or sufficient for the final answer. Real-phone RAM,
load time, heat, and battery are still untested.

## Accepted architecture decision: relevance gate

Accepted on 2026-08-27 after owner review of Gate 3C.5:

```text
question + one offered memory piece
→ Qwen3-Reranker-4B Q4
→ TAKE / NOT SURE / DROP
```

Rules:

- `TAKE` moves the piece to later evidence checks; it does not call it true.
- `NOT SURE` is preserved and sent to a later module; it is never silently
  deleted.
- `DROP` removes the piece only from this answer attempt; it does not erase the
  owner's memory.
- This module may be replaced later without changing the capsule or relay
  contract.
- Q4 is the accepted build because it preserved all 24 BF16 decisions at 2.50
  GB. Actual-phone runtime remains a required deployment check.

## Accepted architecture decision: claim-support gate

Accepted on 2026-08-28 after owner review of Gate 3C.6P–Q:

```text
exact verified source passage + one atomic pocket i claim
→ DeBERTa-v3-base NLI
→ SUPPORTED / CONTRADICTED / NOT PROVEN
```

Rules:

- Ordinary code first proves that the passage really came from the named
  source snapshot. The NLI model never replaces this byte check.
- The premise contains only the exact source passage. The person's question
  stays outside this model call.
- The hypothesis is one short, human-readable claim. It must not contain two
  conclusions joined together.
- `SUPPORTED` means only that the passage supports the claim. It does not prove
  that the source is true, current, independent, applicable, or safe to share.
- `CONTRADICTED` is preserved as evidence of disagreement. It is not silently
  deleted.
- `NOT PROVEN` means the passage does not settle the claim. It does not mean
  that the claim is false.
- This module is replaceable. Its input and three output states are the stable
  harness contract.
- Do not concatenate the person's question and surrounding document into this
  NLI call. On the same 20 frozen cases, the short pair scored 20/20; the mixed
  package scored 15/20, and a human confirmed all five new errors.

Evidence boundary: this is a synthetic English development result checked by
one researcher. It does not yet establish multilingual quality, independent
labelling, phone performance, long-document behaviour, or production safety.

## Accepted Gate 12A: knowledge revision chains

The owner accepted Gate 12A as the narrow chain mechanism.
Each pocket i can send an append-only chain whose parent links identify its
current head and preserve older claims as history. The verifier correctly
handled ten frozen cases, including replacement, retraction, missing history,
a fork, out-of-order delivery, and two independent conflicting lineages.

Result: 10/10 case decisions, 10/10 exact JSON roundtrips, zero wrong heads,
and zero lost history revisions. This does not yet test signatures, hostile
peers, truth, or scale.

Gate 12A.2 removed all semantic relation labels. The minimal candidate record
now contains only author, chain id, revision id, direct parent, claim, evidence
pointer, active state, and permission. One frozen three-record chain travelled
from yukabox to miracle-prod. The receiver independently selected `PHY-R3`,
kept `PHY-R1` and `PHY-R2` as history, and returned the same payload SHA-256.
This is one physical SSH-carried development transfer, not the final relay.

Gate 12 does not decide whether the latest claim is true, applicable, or
independent. Those questions are intentionally deferred until the harness has
collected all candidate answers.

## Failed Gate 13A: merging similar answers

Gate 13A froze 21 English and Russian answers before the run: six groups of
three paraphrases, three single answers, and five pairs that must never be
merged. A frozen multilingual MiniLM embedding model selected candidate pairs;
a threshold calibrated on separate examples turned those pairs into connected
groups.

The locked gate failed: 0/6 paraphrase groups were recovered exactly, pairwise
F1 was 0.395062, and 4/5 forbidden merges occurred. No answer was lost. The
largest wrong group joined four different claims merely because all discussed
image tiling.

Decision: embedding similarity may propose answers for comparison, but it may
not perform the final merge. The next merge module must compare the actual
claims and preserve opposing or merely related meanings.

## Failed Gate 13B: conservative DeBERTa piles

Gate 13B reused the already opened 14-answer English subset so DeBERTa could be
compared directly with Gate 13A. Every pair was classified in both directions.
Two answers entered the same pile only when each entailed the other, and each
new answer had to match every existing pile member.

This was much safer but missed the locked gate: 4/6 paraphrase piles were exact,
pairwise precision was 1.0, recall 0.666667, F1 0.8, and there were 0 forbidden
merges or lost answers. Two real paraphrase pairs split because one direction
was classified neutral.

The run also produced 19 `opposing_versions` edges, including obviously
unrelated claims. This dataset did not contain a separately labelled conflict
exam, so those edges are not evidence that DeBERTa can map disputes. Decision:
mutual entailment is a promising conservative merge check, but Gate 13 still
remains open. A fresh test must separately measure same, different, and truly
contradictory versions before conflict links reach users.

## Failed Gate 13C: meta-NLI second pass

Gate 13C tested the owner's proposed second look at the ten piles from Gate
13B. Each pile pair became one premise, and DeBERTa judged the fixed hypothesis
`Pile A and Pile B express the same claim.`

The second pass recovered both missed paraphrase pairs, but it also approved 42
false merges. It returned entailment for 44/45 pile pairs, connected every
answer into one final group, and recreated all four forbidden merges. The
locked gate failed.

Decision: this DeBERTa checkpoint must not judge meta-statements about groups.
Literal source/claim NLI and meta-level equivalence are different tasks. Keep
Gate 13B's conservative piles for now; do not add this second pass to the
accepted harness.

## Gate 13D: accepted guarded Qwen canonicalization sandwich

Gate 13D tested `DeBERTa piles → Qwen3-0.6B canonical claim → bidirectional
DeBERTa validation → bidirectional DeBERTa pile comparison`. The first preflight
used invalid right padding and is preserved separately. A frozen correction
changed only Qwen batching to left padding before the valid run.

The valid run improved exact paraphrase piles from 4/6 to 5/6, recovered 1/2
missed merges, and made zero false or forbidden merges. It still failed the
locked gate: only 9/10 Qwen claims passed validation.

Manual inspection found that the guard correctly blocked Qwen when it changed
`can indicate swarm preparation` into the certain `the colony is preparing to
swarm`. Another accepted rewrite dropped `exclusively`; the owner judged that
acceptable in this particular affirmative instruction because the remaining
sentence still stated the correct action. This is a case decision, not evidence
that losing exclusivity is harmless in every domain. The one recovered merge
was also fragile: its deciding direction was entailment 0.505623 versus neutral
0.493628, while the text barely changed.

Owner decision on 2026-08-29: accept the four-stage sandwich as the current MVP
architecture. Original answers, evidence, sources, and lineage always remain;
Qwen's canonical claim is only a comparison aid. DeBERTa first builds cautious
piles, then validates each Qwen rewrite against every original in both
directions. A failed rewrite is discarded and its original pile survives. Only
validated claims are compared again, in both directions, to form final piles.
Different versions stay separate. The 5/6 synthetic development result remains
an honest limitation, not proof across domains or scale. Decision record:
`/experiments/E007/answer-piles-accepted-architecture-v0.1.json`.

## Accepted steps and their evidence

| Step | Accepted design | Current evidence |
| --- | --- | --- |
| 1 | Install one modular app and choose a model preset. Start with Qwen 0.6B; stronger devices may choose a larger model. | Agreed, not built. |
| 2 | Keep the person's exact question. Do not silently rewrite it into another request. | Passed on MacBook + yukabox. |
| 3 | Use Speculative Attention and public capability cards to ask many plausible pocket i in parallel. | Delivery and simple ranking passed; automatic cards and scale remain open. |
| 4 | Search only owner-approved local memory. The complete private store stays on the device. | Physical local-search transport passed on two devices. |
| 5 | An online pocket i returns `found`, `empty`, `blocked`, or `error`. If nothing arrives before the deadline, the relay records `offline`. | Receipt states and a synthetic blocked secret passed. |
| 6 | A useful offer travels as a readable capsule: claim, evidence, source, lineage, conditions, limits, and permission. | Exact stored-capsule transport passed; extraction from messy memory remains open. |
| 7 | Prefer recall at the sending edge: a doubtful candidate may travel, because the receiver can filter it; missing useful knowledge is harder to repair. | New-question send-policy smoke passed. |
| 8 | Before any network send, a separate security module enforces owner permission and removes secrets. | Contract accepted; only a synthetic canary has been tested. |
| 9 | The receiver checks `question ↔ one memory piece` with Qwen3-Reranker-4B Q4 and returns TAKE / NOT SURE / DROP. | Accepted after Gate 3C.5; Q4 matched BF16 24/24. Phone test pending. |
| 10 | Ordinary code proves that the exact passage came from the named, versioned source snapshot and byte range. | Gate 3C.6A passed 20/20 twice with identical output. |
| 11 | Check `exact source passage ↔ one atomic claim` with DeBERTa-v3-base NLI. Keep the person's question outside this call. Return SUPPORTED / CONTRADICTED / NOT PROVEN. | Accepted after Gate 3C.6P–Q: short pairs 20/20; the mixed question-and-context package fell to 15/20. Synthetic English development evidence only. |
| 12 | A pocket i's knowledge history is an append-only chain: current head plus preserved history. No semantic relation label is required. Truth, applicability, and independence are checked later after collection. | Accepted after 10/10 synthetic mechanics and one yukabox → miracle-prod transfer with matching SHA-256 and correct head/history. |
| 13 | Build cautious DeBERTa piles, let Qwen create one readable claim per pile, validate every rewrite against every original in both directions, then compare only validated claims to form final piles. Preserve originals, evidence, sources, lineage, and separate versions. | Accepted for harness v0.2 by the owner after Gate 13D: 5/6 exact paraphrase piles, 0 false merges, 9/10 rewrites validated. Synthetic development evidence only; scale and domain transfer remain unproven. |
| 14 | With Qwen3-1.7B, produce a readable answer containing only claims supplied by accepted piles. Preserve separate versions. Empty input bypasses the model and returns a fixed response. | Accepted by the owner after the paired Gate 14A.2 result: 1.7B passed 10/10 versus 8/10 for 0.6B, with 0 invented facts. Synthetic English development evidence only; full-pipeline and phone tests remain open. |
| 15 | Record `contacted → found → accepted → used → answer improved` so routing learns realized value rather than popularity. | Metric contract accepted, learning loop not built. |

## Locked Gate 14A: closed-world answer synthesis

Gate 14A freezes ten English synthetic cases before the first model run. Eight
contain accepted piles and two are empty. Qwen3-0.6B may make the supplied
claims readable and connect them, but may not add facts, conclusions, advice,
or statements about what remains unknown. Separate versions must remain
separate. Empty input bypasses the model and returns one fixed response.

The manual gate is strict: all required meanings preserved, no new factual
meaning, numbers/negation/uncertainty/conditions preserved, 2/2 canned empty
responses exact, and no truncated output. DeBERTa support and coverage scores
are diagnostics only. Protocol:
`/experiments/E007/answer-synthesis-protocol-v0.1.json`; frozen cases:
`/experiments/E007/answer-synthesis-world-v0.1.json`; UI:
`/experiment/e007/gate-14a/`.

The locked run returned 8/8 non-empty answers, 2/2 exact canned empty answers,
and no truncation. Manual review passed 8/10. Qwen invented no new factual
claim, but S02 removed the explicit framing that two claims were separate
supported versions, and S08 omitted the second pile completely. Therefore the
strict gate failed. The next design should synthesize one pile at a time and
let ordinary code preserve pile order and version labels, so a language model
cannot silently delete a pile. Raw result:
`/experiments/E007/answer-synthesis-result-v0.1.json`; audit:
`/experiments/E007/answer-synthesis-human-audit-v0.1.json`.

Gate 14A.2 is a paired repeat frozen before the first Qwen3-1.7B run. It reuses
the same ten cases, prompt, deterministic empty path, decoding settings, and
manual rubric. The only intended change is Qwen3-0.6B → Qwen3-1.7B at pinned
revision `70d244cc...1ad5e`. It passes at 10/10 and beats the 0.6B baseline only
if it scores above 8/10 without more invented facts. Protocol:
`/experiments/E007/answer-synthesis-qwen17b-protocol-v0.1.json`.

The paired run passed 10/10 by the same manual rubric, versus 8/10 for 0.6B.
Qwen3-1.7B restored the explicit two-version framing in S02 and retained the
second pile in S08. It added no new factual claim, returned 2/2 exact canned
empty responses, and hit no token limit. This supports offering model-size
presets, but it validates only this synthetic final-synthesis set—not the full
harness. Result:
`/experiments/E007/answer-synthesis-qwen17b-result-v0.1.json`; audit:
`/experiments/E007/answer-synthesis-qwen17b-human-audit-v0.1.json`.

Owner decision on 2026-08-29: accept Gate 14 for harness v0.2 with the pinned
Qwen3-1.7B preset. Do not accept free-form multi-pile synthesis on 0.6B. The
writer may only restate supplied claims; it may not invent missing information.
Original piles and evidence remain authoritative. Decision record:
`/experiments/E007/answer-synthesis-accepted-architecture-v0.1.json`.

## Remaining before the first end-to-end MVP

1. Package one installable Pocket i app with pinned model presets and clean
   install/update/uninstall paths.
2. Measure the quantized 1.7B writer and 4B reranker on the actual phone.
3. Turn owner-approved local files into a private searchable store and a safe
   public capability card without exposing the files.
4. Integrate permission, secret filtering, capsule transport, relevance,
   source anchoring, NLI, history, piles, and final synthesis into one run.
5. Connect MacBook, yukabox, and phone through one authenticated room with
   receipts for found/empty/blocked/error/offline.
6. Run a locked end-to-end comparison, publish every intermediate decision,
   and show question, contacted pocket i, evidence, versions, and final answer
   in one simple UI.

## Locked Gate 15A: the complete route failed

Gate 15A connected the already accepted pieces over all 30 frozen E007
questions and 64 logical pocket i. Qwen3-1.7B wrote the short claims and final
answers; the 4B reranker, ordinary source-anchor code, and DeBERTa kept their
separate jobs.

The mechanical chain worked, but the meaning chain did not. All required
sources were found and no secret leaked, yet 332 uncertain passages travelled
onward. A claim could be perfectly supported by its own source while still
belonging to another device. This produced only 10/30 completely correct final
answers. Gate 15A is rejected and preserved. Before an app MVP, the harness
needs a tested gate for `question identity and conditions ↔ source identity and
conditions`.

The stage audit identifies two separate repair targets. Step 5 preserved recall
but admitted 345/420 extra passages. Step 6 retained only 34/60 required claims
after Qwen rewrites were checked against their exact sources. Do not retest the
whole chain yet: isolate relevance first, then claim extraction on clean required
sources. Piling and final synthesis cannot be judged fairly until those inputs
are repaired.

## Rejected Gate 15B relevance replacement

Qwen3-1.7B was tested once on the same 480 frozen question-fragment pairs as a
two-word relevance gate. It cut extra passes from 345 to 47, but lost seven of
sixty required fragments and missed both locked thresholds. Manual review also
showed that `required` and ordinary-language `relevant` are not identical:
eighteen mechanically extra fragments described copied reports from the exact
same disputed case. Keep the locked failure and raw 480 decisions. Do not place
this direct binary gate in the accepted harness. The next relevance contract
must name the answer slot being filled and score truly unrelated, redundant,
and condition-mismatch records separately.

Gate 15C changed only Qwen3-1.7B to server-side Qwen3-8B on the same 480 pairs.
The larger model kept 41/60 required fragments and passed 18/420 extras. It
rejected all clearly unrelated records, but also rejected every one of fifteen
conditional safety rules in the error set plus four next-measurement rules.
The unchanged binary `directly helps` contract is rejected for both model
sizes. Do not solve this by choosing a larger server model. Define the missing
answer slot before judging a fragment, then permit useful multi-fragment
composition.

Gate 15D tested that composition directly by showing Qwen3-8B all sixteen
fragments for one case together. It retained 30/30 core pieces and 30/30
conditional action or next-measurement pieces, while retaining 0/396 frozen
irrelevant records. Therefore the whole-bundle view repairs the pairwise
`evidence X → condition X → action Y` failure.

It is not the complete accepted selector. Qwen removed all 24 same-case
alternatives and the final writer could not cite or faithfully preserve them.
The core answer was right in 30/30, but only 16/30 passed the complete manual
rubric and three answers added unsupported generic alternatives. Preserve two
separate shelves before synthesis: an evidence-landscape shelf with same-case
alternatives and lineage, and a best-supported-answer shelf produced from the
whole bundle. Never let an answer cite the opposing shelf as its evidence.

## Accepted evidence-ledger law

Owner decision on 2026-08-29: a model may choose what to use, but it may not
decide what ceases to exist. Every consented incoming capsule is appended to an
immutable question ledger after permission, secret, exact-source, and envelope
checks. Model decisions add labels and views; they never delete the capsule.

The same ledger has two primary views. `best_answer` contains the strongest
supported cause or explicit uncertainty plus its safe action or next evidence.
`all_versions` preserves same-case alternatives, conditional rules, sources,
and lineage. The visible shelves are `USED`, `SAME_CASE`, `CONDITIONAL`,
`UNCERTAIN`, and collapsed-by-default `OTHER`. Ten copies from one lineage are
one dependent view rather than ten confirmations.

Every factual view must cite evidence from its own shelf. The final writer may
describe a weaker or contradicted alternative, but it may not cite the main
view's opposing source as evidence for that alternative. Accepted decision:
`/experiments/E007/evidence-ledger-accepted-architecture-v0.1.json`.

Gate 15E is the next test and requires no new model inference. Build both views
from the preserved Gate 15C and 15D traces. It must retain all sixty required
pieces and all twenty-four same-case alternatives, keep the 396 other fragments
available for audit but hidden by default, and collapse dependent copies by
lineage. Only after this ledger mechanics pass should a writer receive both
shelves in Gate 15F.

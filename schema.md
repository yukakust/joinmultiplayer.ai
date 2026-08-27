# Pocket i harness — agreed path

Status: working architecture agreement after E007 Gate 3C.5. This is not a
claim that every module already exists or has passed a physical-device test.

E007 Gate 3C.6A.2 adds one development finding about local source retrieval:
do not cut memory into isolated equal-size word blocks. Preserve document
structure and overlapping neighbour context, then keep exact source ranges.
This improved complete retrieval from 6/10 to 9/10 and required-atom recall
from 9/14 to 14/14 in one synthetic English manual. It is not accepted as a
finished cutter: one neighbouring opposite rule for Aster-8 also survived an
Aster-9 query, so a later condition/entity check is still required.

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
| 10 | Later validators check source support, truth, matching conditions, provenance, and independence. Start by proving that a fragment came from one exact source snapshot. | Gate 3C.6A passed 20/20 twice with identical output; owner review pending. |
| 11 | Similar claims collapse, but evidence and lineage remain. A supported minority stays visible. | Accepted design, not yet tested at scale. |
| 12 | A model writes the final human answer only from accepted evidence; a final checker shows gaps instead of guessing. | Accepted design, not yet tested. |
| 13 | Record `contacted → found → accepted → used → answer improved` so routing learns realized value rather than popularity. | Metric contract accepted, learning loop not built. |

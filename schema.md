# Pocket i harness — agreed path

Status: working agreement after E007 Checkpoint 3A. This is the contract we are
building next, not a claim that every module already exists.

## The whole path

```text
Person writes one question
        ↓
Harness keeps the exact text
        ↓
Speculative Attention asks likely pocket i
        ↓
Every contacted pocket i replies
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

## 4. Every contacted pocket i replies

Silence is not the same as finding nothing. Each contacted pocket i therefore
ends in one visible state:

| State | Meaning |
| --- | --- |
| `found` | A permitted candidate was found and a capsule was sent. |
| `empty` | Search completed honestly and found nothing useful enough to send. |
| `blocked` | A candidate exists, but policy does not allow sending it. |
| `error` | The pocket i received the question but could not finish. |
| `offline` | The relay received no response before the deadline. |

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

E007 Checkpoint 3A has demonstrated exact-question delivery and public-card
ranking for four processes on two physical devices. It has not yet demonstrated
local memory search, safe capsules, evidence validation, deduplication, answer
improvement, or scale. Those are later checkpoints of this schema.


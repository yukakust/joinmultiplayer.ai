# E005 protocol v0.1 — Signal in the Swarm

Status: **FROZEN BEFORE PUBLIC DEVELOPMENT DATA**  
Parent: E004  
Claim class: synthetic development until a separately committed locked run

## Question

Can a growing swarm find the right combination of understanding and evidence,
preserve a well-supported minority, and avoid treating dependent copies as
independent consensus?

Russian:

> Может ли растущий swarm находить правильное сочетание понимания и
> доказательств, сохранять обоснованное мнение меньшинства и не принимать
> множество зависимых копий за независимый консенсус?

## Separation of responsibilities

- The frozen base provides language and general reasoning.
- A personal DoRA adapter learns a stable skill: interpreting a domain,
  reformulating a search, comparing versions, evaluating sources, or applying a
  procedure. It must not see locked facts or locked answers.
- Local RAG stores exact, mutable, attributable, and deletable records.
- The router predicts the marginal usefulness of candidate pocket i.
- The merger builds a claim-and-evidence graph. It does not count raw votes as
  independent evidence.

## Public natural-language world

The public development world uses fictional devices, places, and protocols that
could not have appeared in the base model's training data. Questions paraphrase
the records and include:

1. a copied false majority versus a current primary-source minority;
2. a correct consensus supported by independent lineages;
3. an attractive but unsupported minority that must not receive false balance;
4. a stale exact lexical match versus a current semantic match;
5. a question requiring complementary skills and evidence from multiple pocket i;
6. insufficient evidence, where the correct action is to abstain.

A separate prior-conflict stress split may later contradict plausible base-model
assumptions. It must never be merged into the neutral-world headline metric.

## Pocket contract

Each pocket i owns:

- one capability card earned from held-out calibration tasks;
- one local RAG shard;
- a source-lineage graph for those records;
- an optional personal DoRA adapter trained only on transferable procedures;
- an append-only outcome history.

Self-reported confidence or expertise is not accepted as evidence. The router
may use calibrated performance, source availability, freshness, latency, and
lineage diversity.

## One-round network contract

Candidate discovery uses a periodically updated safe capability index. It is not
an inference round. The source chooses a bounded candidate set and sends the
question to all selected pocket i once, in parallel. Each returns one capsule:

```json
{
  "claim": "calibrate_with_niv_3",
  "evidence_ids": ["DOC-017"],
  "source_lineages": ["LINEAGE-MANUAL-K7-CURRENT"],
  "source_dates": ["2142-04-18"],
  "capability": "thermal relay diagnostics",
  "confidence": 0.74,
  "limitations": ["no maintenance history"]
}
```

Raw private memory is never part of a capsule. All selected pockets answer in
parallel; there is no multi-round model discussion.

## Deterministic minority-report policy

Before a learned merger is allowed, the harness constructs a claim graph and
reports:

- raw supporter count;
- independent source-lineage count;
- primary/current source count;
- stale or withdrawn source count;
- calibrated capability support;
- contradictions and missing evidence.

An alternative is shown only when it is material and has at least one credible
independent evidence lineage that has not been defeated by a stronger current
source. Random dissent is not promoted merely to appear balanced. If the
minority has stronger evidence, it becomes the main answer and the numerical
majority is described as dependent or stale.

## Compared systems

1. lexical nearest record;
2. semantic retrieval only;
3. raw majority vote;
4. highest calibrated expertise only;
5. evidence-aware router without personal DoRA;
6. DoRA + local RAG + evidence-aware router + claim merger;
7. oracle candidate set and oracle evidence graph.

## Required ablations

- remove personal DoRA;
- remove local RAG;
- hide lineage metadata;
- duplicate one wrong lineage 20 times;
- remove the credible minority;
- remove one necessary complementary specialist;
- replace the current source with its stale predecessor;
- swap fictional entity names while preserving meaning.

## Scaling curve

Run the same committed task families with 8, 16, 32, 128, and 512 available
pocket i. More pockets may add useful capabilities or correlated noise. Active
compute and network bytes are recorded, but the scientific claim concerns the
growth of total swarm resources rather than equal-compute superiority.

## Metrics

Primary:

- final answer accuracy;
- required-complement set recall;
- credible-minority preservation recall;
- false-minority report rate;
- copied-majority resistance;
- evidence precision and recall;
- routing regret against the oracle.

Secondary:

- calibration error;
- update and deletion response accuracy;
- citation/claim entailment;
- active pockets, bytes, latency, and source-lineage diversity;
- marginal contribution when each selected pocket i is removed.

## Development gates

### Gate 0 — protocol

Protocol, claim boundary, controls, and metrics are committed. **No training.**

### Gate 1 — public world

All public records, paraphrased questions, source lineages, expected claim maps,
and copied-majority traps are visible on joinmultiplayer.ai. The owner reviews
them by eye. **No training.**

### Gate 2 — base-only preflight

The frozen base answers without RAG or adapters. Any neutral-world item it can
answer reliably is excluded before later data are locked.

### Gate 3 — deterministic harness

Lexical, semantic, majority, evidence-graph, and oracle controls run without
personal weight updates. Failure artifacts remain public.

Status: **development run complete; owner visual review accepted and artifact
frozen on 2026-08-24**. The source selection and frozen-generation stages are
reported separately. Perfect source selection did not guarantee a correct
generated action. The evidence graph matched the oracle only inside the curated
synthetic fixture, where lineage, freshness, and expected claim structure were
predeclared. No further retrieval tuning belongs in Gate 3 v0.1.

### Gate 4 — procedure learning

Surrogate pocket i train personal DoRA skills on examples that are disjoint from
evaluation facts, entities, source texts, and answers. The site shows before and
after on held-out procedure tasks.

Before training, publish one owner-readable checkpoint containing the exact
skill being taught, examples visible to the adapter, held-out examples it cannot
see, the frozen-base control, and the pass/fail rule. Preparing this checkpoint
does not authorize training; the owner starts training only after inspecting it.

Status: **design v0.1 approved; synthetic data frozen; zero weights changed at
the checkpoint**.
The visible checkpoint is `/experiment/e005/gate-4/`; its machine-readable
artifact is `/experiments/E005/gate-4-design-v0.1.json`.

### Gate 5 — learned routing and merging

Router and merger train only on surrogate pockets. Frozen response-capsule and
minority-report contracts remain enforced by the harness.

Gate 5A first isolates the smaller composition claim. Two pocket i receive
different, necessary halves of each task. Neither pocket, the frozen base, nor
an intentionally wrong pair may solve the complete task reliably. The selected
pair answers once in parallel; a frozen merger receives only their bounded
capsules and the public question. Success requires the correct pair to beat
every single-pocket and wrong-pair control on a locked set. This is a test of
complementary composition, not yet learned routing or swarm scaling.

Gate 5A.2 closes the user-answer gap left by Gate 5A. The same trained pockets
answer a newly locked set, then frozen Qwen receives the public question and
their two raw capsules. It must produce one natural answer that preserves both
facts and exposes neither JSON nor field names. Question-only and missing-one-
capsule controls test whether the source model invents absent knowledge. This
remains explicit text-capsule synthesis, not learned or latent merging.

Gate 5A.2 failed. CAUSE-I and SAFETY-I still emitted their raw capsules, but the
frozen source Qwen preserved both required facts in only 4 of 24 natural answers
under human review (the frozen phrase checker counted 1 of 24). The preregistered
gate required 20 of 24. English scored 4 of 12; Russian scored 0 of 12. Even the
oracle capsules scored 4 of 24 under the same human review, isolating the failure
to the final language synthesizer rather than to capsule retrieval alone.

This result is public at `/experiment/e005/gate-5a/human/results/`. Every raw
answer remains visible. Gate 5B must not begin until a source merger is tested on
this unchanged exam without changing the questions or pocket capsules.

Gate 5A.3 isolates the interface failure. It reuses the same questions and
trained adapters, but a frozen public codebook expands each actual label into a
short meaningful claim with pocket provenance. The answer budget is 192 tokens.
Frozen Base and instruction-trained Qwen are compared; missing-capsule and
question-only controls remain. This is still a text protocol, not the planned
parallel neural-track architecture.

Gate 5A.3 failed but improved the interface result. Human review scored the
semantic-capsule Base at 11/24 and instruction-Qwen at 17/24, below the locked
20/24 threshold. The previous coded Base interface scored 4/24. Instruction
Qwen scored 11/12 in English and 6/12 in Russian; none of its main answers hit
the 192-token limit. Question-only and either-capsule-missing controls scored
0/24. The semantic codebook helped, but a 0.6B final merger remained unreliable.

Gate 5B is frozen as the first real hidden-state track experiment. Qwen's 28
layers are split into shared stem 0–5, personal middle tracks 6–21, and shared
tail 22–27. Each personal track receives only rank-8 DoRA updates. The merger
combines bounded `track_i(h) - z0` residuals; no text capsule crosses the track
boundary. The first run is a one-computer simulation before physical-network
replication. The curriculum contains 256 track lessons and 192 disjoint merger
lessons; the locked bilingual exam contains 32 unseen devices and prompts.

The real-model preflight passed before training. Each personal path contains 112
DoRA-wrapped linear modules and 3,080,192 trainable personal parameters. Both
fresh deltas and the maximum logit difference from untouched Qwen were exactly
zero. Selecting CAUSE-I or SAFETY-I exposed trainable parameters only inside the
selected middle path.

Training smoke v0.1 stopped before its first optimizer step because the chat
template made the assistant-target mask empty; no weights changed. The corrected
v0.2 smoke ran two steps per track. CAUSE-I loss moved 5.988→4.509 and SAFETY-I
5.818→3.275. Shared Qwen stayed unchanged, and training SAFETY-I did not change
CAUSE-I. The merger and locked exam remained untouched.

The full personal-track checkpoint then ran two passes over 128 lessons per
track. Mean CAUSE-I loss moved 2.056→0.00036 and SAFETY-I 2.406→0.00066. The
shared model stayed unchanged, and CAUSE-I stayed byte-for-byte unchanged while
SAFETY-I learned. This is a training result only: the merger and locked exam were
still untouched.

The hidden-state merger smoke loaded both saved tracks, froze them, and ran two
steps on four merger lessons. Loss moved 2.865→1.280; only the 395,650 merger
parameters changed. The locked exam remained untouched.

The full merger checkpoint ran two passes over all 192 merger lessons. Mean
loss moved 1.138→0.642. Both personal tracks remained unchanged and only the
395,650 merger parameters moved. This modest training result was published
before opening the locked exam.

Before opening the exam, evaluation protocol v0.1 froze greedy decoding, 40 new
tokens, all six conditions, an alternating CAUSE×CAUSE / SAFETY×SAFETY wrong
pair, and a provisional exact-statement score followed by required human review.

Execution attempt v0.1 generated three untouched-base answers and was stopped
only because one-question-at-a-time decoding would overrun the compute window.
No weights, exam items, decoding rule, or thresholds changed. v0.2 batches
independent questions while preserving the frozen inference semantics.

Execution attempt v0.2 with batches of eight was also stopped because it filled
swap and became slower. The completed run used batches of two. Its provisional
strict score was: shared 0/32; each single 0/32 complete; wrong pair 0/32; text
capsules 4/32; correct neural pair 2/32 against the frozen 26/32 requirement.
CAUSE-I still supplied its half on 32/32 paired answers, while SAFETY-I survived
only 2/32. The first merger therefore failed by silencing one personal track.
All 192 raw answers await human review.

Gate 5B.1 corrected only decoding. Forty-one records that reached the original
40-token ceiling were deterministically regenerated with the same frozen prefix
and an emergency ceiling of 256. All 41 extended; 40 ended naturally and one
base-Qwen Russian answer reached 256. No correct-neural-pair record had been cut
off, so its result did not change. Literal counts also stayed unchanged. Human
review identified `G5B-LOCK-EN-06` text capsules as a clear false negative: both
facts were present as a paraphrase, not as the two exact expected sentences.

Gate 5B.2 is locked before any LLM judge sees the answers. It replaces the
literal score as a claim about meaning, but preserves it as a reproducible text
check. A pinned Mistral Small 3.2 24B and a pinned Phi-4 Mini independently see
one anonymous answer at a time. They must separately label the cause, safe
action, contradiction, and overall result, and copy exact supporting quotes from
the answer. Both must first pass 12/12 synthetic calibration traps. The owner
reviews every disagreement plus 24 deterministically sampled agreements. More
than two owner corrections in that sample expands review to all answers. The
original Gate 5B thresholds do not change; only the correctness measurement is
repaired. The frozen protocol is public at
`/experiment/e005/gate-5b/semantic-review/`.

The Gate 5B.2 Vast preflight then passed before model download. Two RTX 3090
GPUs were visible and a real CUDA tensor operation succeeded. The temporary
machine had 54 GiB free after installing the pinned software environment. It has
no persistent volume, so judges must run sequentially and each result must be
copied off the instance immediately. No judge had seen an experiment answer.

Judge J1 then stopped at calibration v0.1 with 8/12. It saw zero experiment
answers. The four failures exposed ambiguity in the ruler itself: the written
overall rule and its expected labels disagreed about one preserved half, and
`absent` versus `incorrect` was not defined sharply enough. This is preserved as
an infrastructure/scoring failure, not an E005 model result. A corrected rubric
may use only these synthetic cases; it must be committed before recalibration.

Rubric v0.2 therefore makes each judge label only `cause` and `safe_action`.
`incorrect` now means an explicit denial or conflicting alternative; `absent`
means no relevant claim. Non-absent labels require exact quotes. Deterministic
code, not the LLM, derives contradiction and overall correctness. The same 12
cases and 12/12 requirement remain unchanged.

J1 also stopped on rubric v0.2, now at 9/12 and still before all experiment
answers. It continued to label a missing cause as an incorrect cause and rejected
one valid Russian paraphrase for not literally saying "cause". The pass threshold
will not be lowered. v0.3 must freeze a mechanical decision order and a fresh
unseen synthetic calibration set before another attempt.

Rubric v0.3 is frozen before the third calibration. For each half, the judge
must ask in order: is there a relevant claim; does it explicitly conflict; does
it preserve the expected meaning as a paraphrase; otherwise is it unclear.
Silence is never a contradiction. A fresh bilingual 12-case set uses thermal
rebound and a closed auxiliary vent, not the facts from v0.1/v0.2. The threshold
remains 12/12 and no E005 answer may be opened first.

Mistral J1 then failed v0.3 at 8/12 while still seeing zero E005 answers. In two
cases its prose said the answer affirmed the expected cause while its structured
label marked that cause incorrect. A fourth Mistral prompt revision is forbidden;
the already-pinned independent Phi judge is calibrated next on unchanged v0.3.

Phi J2's first process stopped before model load because the repository's
optional remote Python code was incompatible with the pinned Transformers
environment. It saw zero calibration cases and zero E005 answers. The retry uses
the same pinned weights through Transformers' built-in Phi-3 implementation;
the rubric, weights, and decoding do not change.

The built-in loader succeeded, but Phi's first calibration output repeated the
expected sentences inside the label fields instead of choosing a closed label.
It scored zero cases and saw zero E005 answers. The retry enforces the already
published JSON schema and enum during decoding with lm-format-enforcer 0.10.12;
semantics, cases, model weights, and the 12/12 gate remain unchanged.

Constrained decoding fixed the label vocabulary, but Phi then selected a
non-absent safe-action label with a null supporting quote on all retries. Zero
cases were scored and zero E005 answers were seen. One final transport-only retry
will include the exact validator error. Another format failure rejects Phi J2.

Phi repeated the same missing-quote failure after the exact validator error was
provided. The precommitted stop was applied: J2 is rejected, scored zero
calibration cases, and saw zero E005 answers. Neither pinned judge is allowed to
score the experiment. A replacement evaluation design requires a new checkpoint.

Protocol v0.4 replaces both rejected judges before any E005 answer is opened.
Judge A is Qwen3 8B BF16 and Judge B is Qwen3 14B BF16. Their prompts hide the
answer-producing model and condition, while the technical protocol keeps exact
model identities and revisions public. A fresh bilingual 12-case calibration
uses seal fatigue and battery disconnection. Each judge still needs 12/12. Both
share one model family, so agreement is redundancy, not independent lineage.

Judge A's first v0.4 process exposed a harness contradiction before any E005
answer: the JSON grammar allowed null quotes while the validator rejected null
for non-absent labels. The semantic score is unavailable. Transport v0.4.1 now
requires a non-empty quote string and represents absence with `__ABSENT__`, which
is normalized to null after generation. No semantic rule or calibration answer
changed.

### Gate 6 — locked final swarm

Generate unseen final pockets and tasks after publishing a commitment. Run the
8 → 512 scaling curve once. Do not tune on locked failures.

### Gate 7 — decision

Publish all systems, ablations, failures, costs, and examples. Advance only if
quality improves with useful swarm growth while correlated noise does not gain
false epistemic weight.

## Stop conditions

Stop and preserve the failure if:

- training facts overlap evaluation facts or answers;
- a claimed independent lineage is actually copied;
- the public development set is presented as locked evidence;
- an alternative opinion is generated without attributable evidence;
- private source text appears in a public capsule;
- model training begins before the owner approves Gate 1.

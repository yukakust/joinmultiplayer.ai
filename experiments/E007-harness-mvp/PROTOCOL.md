# E007 — model-agnostic harness MVP

Status: Checkpoints 0 and 1 approved. Checkpoint 2 three-task yukabox smoke and
its three-judge semantic review are public. Checkpoint 3A finished on two real
devices: it isolated the first two harness steps on four processes across
yukabox and the owner's MacBook. All locked development gates passed for the one
preselected question and four manual cards. See `ATTENTION.md`.

## Question

Can one model-agnostic harness help a heterogeneous swarm find distributed
knowledge, share only permitted evidence, preserve disagreement, and assemble a
better answer than one pocket i alone?

## Honest scope

E007 begins with 64 **logical** pocket i on two physical devices:

- P001–P032 live on yukabox and share one local inference runtime;
- P033–P064 live on the owner's MacBook and share another local inference runtime.

Every logical pocket i has its own identity, capability card, policy, private
document store, source lineage, and audit trail. Sharing a runtime does not make
their memories shared. It also does not make them 64 independently trained neural
models. E007 tests the harness around distributed knowledge, not independent
personal weights.

Only routed pocket i execute a model for a question. The other candidates expose
only a safe capability card.

## Thirty locked tasks after owner review

Six tasks will be created for each family:

1. Join knowledge held by two to four pocket i.
2. Reject similar evidence whose conditions do not match.
3. Preserve a well-supported independent minority.
4. Complete the task without leaking a planted secret.
5. Admit that the swarm does not contain enough knowledge.

The fictional world, answers, required sources, source lineages, and planted
secrets will be published and locked before any model runs.

## Five conditions

1. Frozen model without external knowledge.
2. One pocket i with only its own local RAG.
3. Central oracle context with the correct raw documents already selected.
4. Free-text swarm after routing.
5. Full harness: security, atomisation, local RAG, routing, evidence capsules,
   semantic validation, lineage-aware evidence board, merge shelves, synthesis,
   and final verification.

The oracle is a ceiling for composition, not a search system.

## Ten MVP modules

1. Input and model capability check.
2. Security and permission boundary.
3. Divide the task into model-sized atoms.
4. Connectors and local RAG.
5. Discovery and router.
6. Model adapter and local executor.
7. Human-readable evidence capsule.
8. Semantic, provenance, and independence validation.
9. Evidence board and merge shelves.
10. Final verification, visible trace, and owner verdict.

## Proposed development gates

- zero planted-secret leaks;
- all required knowledge holders found in at least 27 of 30 tasks;
- dependent copies never counted as independent votes;
- supported minority preserved in at least 5 of 6 minority tasks;
- honest insufficiency in at least 5 of 6 missing-knowledge tasks;
- the 0.6B harness beats the same frozen model and one-pocket local RAG;
- every configured model family uses the same network contract;
- all raw answers, rejections, failures, traffic, and owner verdicts remain public.

These are proposed development gates, not scientific proof. They become locked
only after owner review.

## Checkpoints

0. Public design and topology — approved.
1. Public fictional world, 64 capability cards, 30 tasks, and expected evidence — approved.
2. Three-question single-device smoke on yukabox — generation complete; owner review pending.
3A. Exact-question delivery and public-card attention on four processes across
    yukabox and MacBook — complete and owner-published. No Qwen, memory, RAG,
    training, or answers.
3B. Local Knowledge Offer: six locked questions, four small permitted local
    libraries on the same two devices, three search lanes, mandatory terminal
    receipts, and evidence capsules — complete and owner-published as L0001.
    The protocol gates passed, but no single lane both exceeded macro-F1 0.80
    and found all five required shareable sources. No merging or final answers.
3C. Compare balanced, recall-first, and marked-candidate send policies on ten
new questions and twenty-four new local records. Lock the world and policy rules
before inference; do not use the Gate 3B miss to choose a numeric threshold.

3C.2. Give frozen Qwen 0.6B each of the sixteen candidates emitted by the
balanced 3C policy. Hide the sender's claim, capsule, score, and expected label.
The receiving model sees only the question and one complete source and must copy
an exact useful quote or return `NONE`.

3C.3. Replace free-form quote copying with deterministic numbered source spans.
The first clean Qwen pass selects one span ID or `NONE`; code retrieves the
exact text. A separate clean pass sees only the question and selected span,
states what each contains, and returns `HELPFUL`, `NOT_HELPFUL`, or `UNCLEAR`.
Run a controlled A/B on the same sixteen 3C.2 pairs before any held-out repeat.

3D. The same three-question model smoke split between yukabox and MacBook.
4. Locked 30-task run.
5. Owner audit and public result.

## Checkpoint 2 observed result

The frozen Qwen3-0.6B Base produced 15 final answers in 433.445 seconds on
yukabox: three locked questions under five conditions. No training or retry was
performed. No answer hit its token ceiling and no planted canary appeared in a
final answer.

This run found a real failure in the first modular harness. Its Qwen-based
support checker rejected all 24 capsules. Several raw checker outputs begin with
`UNSUPPORTED` and then explain that the claim *is* supported. The deterministic
contract correctly obeyed the first token, so the final harness received an
empty evidence board and answered worse than the centralized context and free
swarm. This is preserved as a result, not repaired after seeing the answers.

The raw generation is
`site/experiments/E007/smoke-results-v0.1.json`. Exact phrase matches inside that
file are navigation aids, not semantic grades. Checkpoint 3 must not start until
the owner reads the visible question-and-answer page and records a verdict.

Three independent runs of `gpt-5.6-luna` then scored every final answer with a
locked semantic rubric: 2 fully correct, 1 partly correct, 0 wrong or unsafe.
The aggregate totals out of 18 were: centralized oracle context 17, one-pocket
local RAG 12, routed free-text swarm 12, modular harness 3, and frozen model 0.
All three judges agreed exactly on 14 of 15 answers (Fleiss' kappa 0.933). This
panel is not a blinded or model-diverse scientific review: all judges are
separate runs of the same model family and could see condition names. Their 45
scores and reasons are preserved in `site/experiments/E007/luna-judge-*-v0.1.json`;
the aggregate is `site/experiments/E007/luna-panel-v0.1.json`.

## Checkpoint 3B observed result

Four pocket i on yukabox and MacBook returned all 24 logical receipts (72 search
lane outputs). Exact words found all five required sources but produced 19 false
`found` states. The small multilingual meaning model classified 20/24 states
correctly with macro-F1 0.849673, blocked the synthetic private record, and
found 4/5 required sources. It missed the hive source and produced three false
finds. Every one of the 55 transported evidence fields exactly matched the
selected local record.

The locked gates technically passed because G4 and G5 each allowed “at least
one lane”: the neural lane passed G4 while exact words passed G5. This exposes a
protocol flaw. The result is therefore
`complete_protocol_pass_hypothesis_inconclusive`, not a confirmed hypothesis.
The next protocol must require one locked method to pass both quality gates.

Public result: `site/experiments/E007/local-offer-result-L0001.json`. Raw owner-
published receipts: `/api/public/L0001`.

## Checkpoint 3C.4 — one question versus one source

Gate 3C.3 showed that free-form Qwen 0.6B is not a reliable meaning judge. It
often rewrote a source as if the source already contained facts from the
question. Gate 3C.4 therefore removes free writing from this step.

Three frozen scorers receive only `question + passage` and return one number:

1. the old multilingual embedding similarity;
2. a 0.1B multilingual MiniLM cross-encoder trained for passage ranking;
3. a 0.6B Qwen3 reranker trained for query-passage relevance.

The 16 old calibration pairs set an ACCEPT and REJECT cut for each method. The
new exam contains 24 English pairs: eight useful sources, eight same-field
traps, and eight obvious distractions. Exam labels never set a threshold.
Scores between the two cuts are `UNCLEAR` and must go to a later module.

The protocol and exam are frozen before model download or inference at:

- `site/experiments/E007/relevance-reranker-protocol-v0.1.json`;
- `site/experiments/E007/relevance-reranker-heldout-v0.1.json`.

This tests relevance only. It does not test whether a passage is true, safe to
share, or sufficient for a final answer.

### Observed result

The one-shot held-out run is complete. None of the three methods passed every
locked gate:

- old cosine similarity: 14/24 strict decisions, one useful source rejected;
- MiniLM 0.1B reranker: 15/24, two useful sources rejected;
- Qwen3 0.6B reranker: 14/24, zero useful sources rejected, nine UNCLEAR, one
  same-field trap accepted.

Qwen3 reranker is the best recall-first first filter in this small test, but it
is not a complete acceptance judge. The result is
`site/experiments/E007/relevance-reranker-result-v0.1.json`. A pre-publication
technical run with two implementation errors is preserved separately as
`site/experiments/E007/relevance-reranker-invalid-preflight-v0.1.json` and is
not treated as scientific evidence.

## Checkpoint 3C.5 — can 4B fit the phone role?

Before designing a multi-model cascade, test the simpler possibility: one
stronger reranker may be enough. The already opened Gate 3C.4 exam is reused
only to compare model size and quantization. This is not fresh evidence about
generalisation.

Compare the exact pinned Qwen3-Reranker-4B BF16 model with self-built GGUF
Q4_K_M and Q5_K_M copies. All three use the unchanged calibration rule and
quality gate. A phone candidate must also agree with BF16 on at least 23/24
three-way decisions, add no useful rejection, and remain at or below 3.5 GiB.

The protocol is frozen before model download, conversion, or inference at
`site/experiments/E007/mobile-reranker-protocol-v0.1.json`. Yukabox measures
quality and file size first. A real phone must still measure RAM, cold load,
heat, battery, and wall time before the word “mobile” is earned.

Gate 3C.5 completed once on the already opened 24-pair exam. The original BF16
model and both self-built copies produced the same three-way decision on all
24 pairs. Every version accepted 8/8 useful pieces, accepted 1/8 same-domain
traps, accepted 0/8 obvious extras, rejected no useful piece, and left 6/24
unclear. Q4_K_M is 2.50 GB and Q5_K_M is 2.89 GB; both pass the locked quality
and quantization gates. Q4_K_M is therefore the smaller phone candidate.
With one slot and a 512-token context, Q4 peaked at 4.57 GB resident memory on
yukabox and reproduced the same scores. This is a phone-shaped server setting,
not a phone measurement.

This does not yet prove phone viability or fresh generalisation. The examples
were opened in 3C.4, and no phone has measured load time, peak RAM, heat, or
battery. Result: `site/experiments/E007/mobile-reranker-result-v0.1.json`.

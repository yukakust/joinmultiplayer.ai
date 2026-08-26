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
3B. The same three-question model smoke split between yukabox and MacBook.
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

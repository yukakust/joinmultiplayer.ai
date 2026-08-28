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

Owner decision on 2026-08-27: accept Qwen3-Reranker-4B Q4_K_M as the modular
incoming relevance gate with three outputs: TAKE / NOT SURE / DROP. NOT SURE
must continue to a later module. This decision does not promote the scorer into
a truth, privacy, provenance, independence, or sufficiency judge.

## Checkpoint 3C.6A — did this fragment come from this source snapshot?

Before any NLI or meaning check, test the byte-level source anchor by itself.
The frozen contract checks source id + version, source SHA-256, a half-open byte
range, fragment SHA-256, and the exact UTF-8 display excerpt. It also freezes
failures for changed sources, bad ranges, character/byte offset confusion,
duplicate legacy quotes, Unicode look-alikes, changed line endings, missing
versions, and unreadable sources.

The locked gate is 20/20 correct, 4/4 intact anchors verified, 0/16 broken
anchors verified, no exception, and an identical second run. No model, network,
or meaning judgement participates. Protocol:
`site/experiments/E007/source-anchor-protocol-v0.1.json`.

Gate 3C.6A ran twice from locked commit `8482c5f`. Both result files had the
same SHA-256. The code classified 20/20 cases correctly, accepted 4/4 intact
anchors, and accepted 0/16 broken anchors; the locked development gate passed.
Result: `site/experiments/E007/source-anchor-result-v0.1.json`. Run receipt:
`site/experiments/E007/source-anchor-run-receipt-v0.1.json`. Owner review is
pending; PDF/OCR/web extraction, signatures, source truth, and source meaning
remain outside this result.

## Checkpoint 3C.6A.2 — does cutting destroy the evidence?

Before implementing or running retrieval, compare two cutters on one frozen
synthetic English manual and ten frozen questions. `fixed_45` creates
non-overlapping 45-word chunks. `structure_overlap` keeps headings, paragraphs,
complete lists and tables, then includes the immediate neighbour on each side.
The same frozen Qwen3-Reranker-4B Q4_K_M and the already opened Gate 3C.5
thresholds score both methods. At most three TAKE/NOT SURE windows survive.

The test records required-atom recall, complete questions, whether linked facts
survive in one window, wrong-device evidence, and a false TAKE when the answer
is absent. Protocol and world:
`site/experiments/E007/chunking-protocol-v0.1.json` and
`site/experiments/E007/chunking-world-v0.1.json`. This is locked before
implementation or inference. It is a small synthetic development test, not
evidence about PDFs/OCR, private memory, final answers, or phone performance.

Development result: the locked gate failed. `fixed_45` completed 6/10
questions, found 9/14 required atoms, and preserved 1/5 linked evidence groups.
`structure_overlap` completed 9/10, found 14/14 required atoms, and preserved
5/5 linked groups, but retained one explicitly forbidden wrong-device atom for
CH06. The absent-answer case produced no false TAKE. The frozen success gate
also contained a protocol bookkeeping error: it said 4/4 linked groups while
the frozen questions define five. The protocol is not rewritten after the run;
the failed gate and error remain public. Result:
`site/experiments/E007/chunking-result-v0.1.json`.

## Checkpoint 3C.6B — incoming evidence capsule

The owner accepted a minimal incoming packet with exactly four meaningful
parts: a free-form claim, an exact source window of at most 500 Qwen tokens, an
exact sender-highlighted subrange, and a versioned source locator with byte
coordinates. Conditions are not a required sender-authored JSON field; they
must remain visible in the exact source window for a later receiver-side test.

Before inference, freeze 24 public synthetic English packets: 8 useful intact,
8 misleading intact, and 8 mechanically broken. Useful information appears at
the start, middle, and end of windows targeting 100, 250, and 500 tokens.
Ordinary code first validates every byte range and hash. Only mechanically
valid packets reach the unchanged Qwen3-Reranker-4B Q4_K_M relevance gate; it
sees question + evidence window only, never the sender claim or highlighted
answer. Protocol and frozen packets:
`site/experiments/E007/evidence-capsule-protocol-v0.1.json` and
`site/experiments/E007/evidence-capsules-v0.1.json`. Claim support, source truth,
privacy, sender retrieval, and final answer generation remain out of scope.

The first inference attempt is preserved as invalid: six packets completed,
then a 587-token full prompt exceeded an incorrectly configured 512-token
physical batch. Frozen inputs did not change; the rerun used a 1024-token
context, physical batch, and microbatch. Locked development result: the
mechanical gate classified 24/24 packets correctly, accepted 16/16 intact, and
accepted 0/8 broken. The reranker took 8/8 useful windows, including 493–495
token windows with evidence in the middle/end; it took 0/8 misleading windows,
marked six NOT_SURE, and dropped two. Both locked gates passed. This does not
show that any sender claim is supported. Result:
`site/experiments/E007/evidence-capsule-result-v0.1.json`; invalid attempt:
`site/experiments/E007/evidence-capsule-invalid-attempt-v0.1.json`.

## Checkpoint 3C.6C — two universal semantic links

Do not hard-code fields such as device, person, time, or situation. Instead,
test the two relations that every evidence capsule needs: whether the exact
quote supports the sender's proposed answer, and whether that proposed answer
helps answer the user's question. A frozen Qwen3-0.6B answers each relation
independently with one of three single-token choices: YES, NO, or NOT SURE.
Ordinary deterministic code then combines them: YES + YES becomes TAKE, any NO
becomes DROP, and every remaining pair becomes NOT SURE.

Before inference, freeze 32 synthetic English cases across eight domains. Each
domain contains all four possible yes/no pairs, so quote support and question
helpfulness cannot be confused with each other. The primary locked gate requires
at least 24/32 correct decisions on each link, at least 6/8 useful cases taken,
and no more than one false TAKE among the 24 other cases. Every score, error,
and abstention must remain public. Protocol and world:
`site/experiments/E007/two-link-semantic-protocol-v0.1.json` and
`site/experiments/E007/two-link-semantic-world-v0.1.json`.

This is a synthetic development test. It does not establish source truth,
privacy, multilingual generalisation, phone performance, or real-world
reliability.

The locked development run failed. Qwen3-0.6B chose YES for both links in all
32 cases. It therefore kept 8/8 truly useful packets but also falsely took all
24/24 other packets. Both relation accuracies were 16/32 and the deterministic
final decision was correct only 8/32 times. The frozen gate was not met.

The raw choice scores contain a limited post-run observation, not a repaired
result. For quote support, the mean YES score was about 74% when support was
present and 64% when absent. For claim helpfulness it was about 52% in both
groups, so that branch showed no useful separation. A separately frozen
calibration experiment may test the first signal later; this result must remain
failed. Result and preserved invalid serialization attempt:
`site/experiments/E007/two-link-semantic-result-v0.1.json` and
`site/experiments/E007/two-link-semantic-invalid-attempt-v0.1.json`.

Post-run interface diagnostic, requested by the owner, is preserved separately
and does not alter the locked result. Qwen3-0.6B can physically output NO: it
copied `[NO]` and selected the second word from `YES NO`. But it answered YES to
`2 + 2 = 5`, and its free explanation repeated that Kest-7 must not be restarted
while still claiming that the quote supported the opposite restart-now answer.
Changing the A/B mapping changed the semantic meaning without reliably changing
the chosen letter. The frozen all-YES result therefore combines a prompt/label
bias with a real failure to compare the claim and quote. Diagnostic:
`site/experiments/E007/two-link-semantic-interface-audit-v0.1.json`.

## Checkpoint 3C.6D — three atomic tool decisions

Replace the failed A/B/C semantic interface with three independent, named tool
decisions. Qwen3-0.6B receives only one comparison at a time and must call
exactly one tool: `supported` or `not_enough`. The three comparisons are source
window → proposed rule, current facts → rule condition, and proposed answer →
rule consequence. Ordinary deterministic code accepts the evidence only when
all three calls are `supported`; malformed, missing, multiple, unknown, or
uncertain calls become `not_enough`.

Before inference, freeze 64 synthetic English cases across eight domains. Each
domain contains all eight possible combinations of the three binary relations.
Thus every atomic relation has 32 positive and 32 negative examples, while only
8 complete packets should be used and 56 should not. An additional balanced
eight-comparison audit repeats the same input with the two tool definitions in
opposite orders.

The locked development gate requires at least 48/64 correct decisions for each
relation, at least 6/8 useful packets used, no more than one false use among the
56 traps, zero malformed tool calls, and at least 8/8 order-invariant audit
decisions. Preserve every raw tool call and every failure. Protocol and world:
`site/experiments/E007/atomic-tool-protocol-v0.1.json` and
`site/experiments/E007/atomic-tool-world-v0.1.json`.

This is a synthetic English development test. It does not establish source
truth, privacy, multilingual generalisation, phone performance, or real-world
safety.

The locked development run failed. Only 2 of 208 outputs used the requested
tool-call envelope and 206 were malformed under the frozen parser. The
conservative fallback therefore used 0/8 useful packets and 0/56 traps. Atomic
scores were 31/64 for source → rule, 32/64 for facts → condition, and 32/64 for
answer → consequence. The order audit was invariant on 7/8 comparisons. Raw
result: `site/experiments/E007/atomic-tool-result-v0.1.json`.

A posthoc diagnostic did not rerun inference. It treated a bare exact tool name
followed only by padding as a button press. This recovered 7/8 useful packets,
but also accepted 25/56 traps. Atomic accuracies became 37/64, 34/64, and 44/64;
tool-order invariance fell to 6/8. Formatting was therefore not the only
problem: the model still over-selected `supported`. This diagnostic does not
repair the locked result. Audit:
`site/experiments/E007/atomic-tool-interface-audit-v0.1.json`.

## Checkpoint 3C.6E — ten visible button cases

Repeat the same three-link hypothesis at a scale the owner can inspect by eye.
Freeze exactly ten unique English questions: three complete useful packets and
seven traps covering every single-link failure and several combined failures.
Do not test JSON generation again. For each of the thirty atomic comparisons,
the harness reads the frozen model's next-token scores for the one-token actions
`accept` and `reject`. This turns the choice into a deterministic two-button
interface and removes the formatting failure from Checkpoint 3C.6D.

Ordinary code uses a packet only after three `accept` decisions. The small
development signal is at least 8/10 correct on every link, all 3 useful packets
used, and 0/7 traps used. Regardless of aggregate scores, publish all ten full
packets, all thirty button scores, and all ten final decisions for human review.
Protocol and world:
`site/experiments/E007/atomic-button-protocol-v0.1.json` and
`site/experiments/E007/atomic-button-world-v0.1.json`.

This is a small synthetic English development test for diagnosing behaviour by
eye. It cannot establish statistical reliability or real-world safety.

The compact development run failed in the simplest possible way. Qwen assigned
the higher next-token score to `accept` on all 30 atomic comparisons. It
therefore used all 3/3 useful packets and also all 7/7 traps. Every relation was
correct on 6/10 cases only, and only 3/10 final packet decisions were correct.
The JSON/tool-call formatting problem is absent here; the remaining failure is
the model's all-accept semantic behaviour under this frozen prompt. Result:
`site/experiments/E007/atomic-button-result-v0.1.json`.

## Checkpoint 3C.6F — two-button sanity check

Before changing the semantic architecture again, test whether the exact frozen
button interface can express both decisions at all. Freeze only two English
comparisons. In the first, both sentences say "The box is red," so the correct
action is `accept`. In the second, one says blue and the other says red, so the
correct action is `reject`. Use the same Qwen3-0.6B snapshot, system instruction,
and next-token `accept`/`reject` scorer as Checkpoint 3C.6E. The locked success
rule is 2/2. Protocol and world:
`site/experiments/E007/button-sanity-protocol-v0.1.json` and
`site/experiments/E007/button-sanity-world-v0.1.json`.

This sanity check can reveal a broken or biased interface. Passing it cannot
establish that the model can judge real evidence.

The sanity check passed 2/2. On "red" → "red," Qwen selected `accept` with
99.98% of the probability mass between the two action tokens. On "blue" →
"red," it selected `reject` with 91.96%. The frozen interface can therefore
express both actions on an extremely easy semantic comparison. This narrows the
later all-accept failure: it appears when the comparison contains richer rules,
facts, and consequences, not at the physical button layer. Result:
`site/experiments/E007/button-sanity-result-v0.1.json`.

## Checkpoint 3C.6G — context ladder

Keep the underlying decision trivial and change only its wrapper. Freeze five
levels, each with an `accept` and a `reject` prompt. Every accept source says
Box R-17 is red and every reject source says it is blue; the proposed answer is
always red. Level 0 contains two plain sentences. Level 1 adds the requested
SOURCE, PROPOSED ANSWER, CHOOSE ONE TOOL shape. Level 2 adds a question,
metadata, and a short source window. Level 3 adds a long distractor window with
the colour at the end. Level 4 adds a longer full packet with the colour in the
middle and current facts.

Within each level, the two prompts differ only by the source colour word. Use
the same frozen Qwen3-0.6B and next-token `accept`/`reject` scorer. The locked
success rule is 2/2 at every level and 10/10 overall. Publish each complete
prompt and both button scores. Protocol and world:
`site/experiments/E007/context-ladder-protocol-v0.1.json` and
`site/experiments/E007/context-ladder-world-v0.1.json`.

This synthetic diagnostic can locate a context-tolerance boundary for one
trivial fact. It cannot establish evidence reasoning or real-world safety.

The context ladder passed 8/10 overall and located a first failure. Levels with
39, 68, and 145 prompt tokens passed 2/2. At 513 tokens, the negative case
flipped from `reject` to `accept` (76.12% accept). At 929 tokens it again chose
`accept` for the negative case (57.55%). Every positive case remained `accept`.
Thus the requested SOURCE → PROPOSED ANSWER → CHOOSE ONE TOOL wrapper itself
works; under this repetitive distractor construction, the reject signal was
lost somewhere between 145 and 513 tokens. This is a located diagnostic band,
not a universal context limit. Result:
`site/experiments/E007/context-ladder-result-v0.1.json`.

## Checkpoint 3C.6H — complete prompts under 90 words

Test a practical short packet rather than another length ladder. Freeze ten
unique English cases across ten domains. Every complete prompt contains only
QUESTION, SOURCE, PROPOSED ANSWER, and the short instruction `Choose: approve
or reject`; every prompt must be at most 90 words. Five sources support their
answers and five conflict with, fail to support, or leave them unclear.

Score the one-token actions `approve` and `reject` with the same frozen
Qwen3-0.6B. The locked gate requires 5/5 approve cases, 5/5 reject cases, and
10/10 overall. Publish every prompt and both action scores. Protocol and world:
`site/experiments/E007/ninety-word-protocol-v0.1.json` and
`site/experiments/E007/ninety-word-world-v0.1.json`.

This is a synthetic development test of a short source-to-answer gate. It does
not establish source truth, rule applicability, or real-world safety.

The first execution scored all ten cases but failed before writing a result:
the runner looked for `locked_success_rule`, while the frozen protocol field is
named `locked_success`. No model decisions from that process were retained or
reported. The frozen prompts and success rule were not changed; only the result
collector was corrected before the recorded rerun.

The recorded rerun failed the gate: 5/10 overall. Qwen selected `approve` for
all ten cases. It therefore passed all 5/5 supported answers and failed all 0/5
unsupported, conflicting, or unclear answers. The complete user packets were
53–73 English words; with the fixed system message and chat template, the model
saw 141–161 tokens. Shortening the complete task to well below 90 words did not
remove this first-action bias. This does not show that short evidence packets
are impossible; it shows that this frozen Qwen3-0.6B next-token gate and prompt
are not a usable balanced semantic judge. Result:
`site/experiments/E007/ninety-word-result-v0.1.json`.

## Checkpoint 3C.6I — reverse the same two buttons

Repeat the exact same ten cases from 3C.6H with the same model and the same
labels. Change only their order: the user instruction, definitions, system
message, and scored action list now put `reject` before `approve`.

Interpret the result before inference. At least 9/10 correct with at least 4/5
in each class is semantic success. At least 8/10 switches from the previous
all-approve result to `reject` is a strong order effect. At least 8/10 remaining
`approve` is a strong approve-label bias. Anything else is mixed or unresolved.
This is a paired synthetic development control, not a general model claim.

The paired run produced a strong approve-label signal. All ten earlier choices
were `approve`; after placing `reject` first everywhere, all ten choices were
still `approve`. No decision changed. Accuracy remained 5/10: 5/5 supported
cases and 0/5 reject cases. Therefore the failure is not explained by a simple
first-option preference. In this frozen scorer, the model strongly prefers the
`approve` token or the meaning attached to it. This control does not yet
separate token prior from semantic framing. Result:
`site/experiments/E007/ninety-word-reversed-result-v0.1.json`.

## Checkpoint 3C.6J — mirrored `1` and `A`

Keep the same ten cases and replace the semantic action words with two
single-token symbols. Deck X defines `1 = approve` and `A = reject`. Deck Y
defines `1 = reject` and `A = approve`. The label order stays `1` then `A` in
both decks. Thus a model following meaning must flip its symbol for every
paired case while preserving its semantic decision.

Before inference, define semantic success as at least 18/20, at least 9/10 per
deck, and at least 4/5 for each semantic class. At least 16/20 identical symbol
choices is a strong symbol bias. At least 8/10 pairwise symbol flips without
semantic success means the mapping was followed but evidence judgment failed.

The paired run found a strong `A`-symbol bias. Qwen chose `A` on 16/20 prompts,
changed its symbol in only 4/10 mirrored pairs, and reached 10/20 semantic
accuracy. Deck X scored 5/10 and deck Y scored 5/10. Thus replacing semantic
labels with neutral symbols did not produce a reliable evidence judge; it
moved the preference from `approve` to `A`. This does not distinguish a token
prior from other prompt-format effects. Result:
`site/experiments/E007/numeric-letter-result-v0.1.json`.

## Checkpoint 3C.6K — exploratory mirrored calibration

Reuse the already produced X/Y probabilities in two deterministic ways. First,
translate each chosen label back to its meaning and answer only when both decks
agree; otherwise return `unsure`. Second, calculate each deck's log odds
`log(P(1)/P(A))` and subtract the mirrored margins, so a stable symbol prior
should cancel.

These rules were proposed after the source outputs existed. This is explicitly
post-hoc exploratory analysis, not a new locked test. Any useful result would
still require a fresh validation set.

Both exploratory rules failed on the existing ten pairs. Agreement answered
4/10, returned `unsure` on 6/10, and split its answered cases 2 correct / 2
wrong. Logit subtraction returned semantic `approve` on all ten cases and
therefore scored 5/10. The symbol preference was not a simple constant offset
that these mirrored rules could remove. Result:
`site/experiments/E007/mirrored-calibration-result-v0.1.json`.

## Checkpoint 3C.6L — invented labels `KSEL` and `PTHY`

Hide the familiar action words behind two invented labels. In the main deck,
`KSEL = approve` and `PTHY = reject`. In the mirror deck, the meanings swap.
Their order stays fixed. Both labels tokenize to exactly two tokens, so score
the summed conditional log probability of each complete label.

Use the same ten frozen questions. Semantic success requires at least 18/20,
at least 9/10 per deck, and at least 4/5 for each semantic class within each
deck. At least 16/20 choices of one label is a strong label bias. At least 8/10
pairwise label flips without semantic success means the mapping was followed
but the evidence judgment failed.

The result was mixed and unsuccessful. In the main deck Qwen chose `KSEL` on
all ten prompts, producing 5/10. The mirrored deck scored 3/10. Across both
decks semantic accuracy was 8/20; `KSEL` was chosen 14/20 and labels flipped in
6/10 pairs. Hiding familiar actions behind invented equal-length labels did not
force reliable use of the mapping. Result:
`site/experiments/E007/nonce-word-result-v0.1.json`.

## Checkpoint 3C.6M — button phrases from one to four words

Clarify the task: this gate asks whether a source semantically supports a
proposed answer. Literal substring presence is a different mechanical check.

Compare five phrase families on the same ten cases in both button orders. The
four clean families contain balanced one-, two-, three-, and four-word labels,
with matching token counts inside each pair. Also include the requested
`include / not presented` pair as an unequal-length diagnostic. This creates
100 prompts.

A family passes only with at least 18/20 semantic decisions correct, at least
9/10 in each order, at least 4/5 for each class within each order, and at least
9/10 case decisions stable when order changes. Select the shortest balanced
family that passes. The USER pair cannot be selected because its lengths are
unequal and its wording changes the task toward literal presence.

The locked development run found no usable balanced family. One-, two-, and
four-word pairs each scored 10/20; the three-word pair scored 11/20. These
families almost always selected the positive phrase, so added words did not
create semantic judgment. The unequal `include / not presented` diagnostic
scored 15/20, but fell from 9/10 with the positive phrase first to 6/10 after
the order changed and preserved its semantic decision on only 7/10 paired
cases. It is therefore not selected. This is a negative synthetic development
result, not evidence that every prompt or larger model will fail. Result:
`site/experiments/E007/phrase-length-result-v0.1.json`.

## Checkpoint 3C.6N — specialised MiniLM NLI

Replace generative button-following with a model trained specifically to
classify a premise and hypothesis as entailment, contradiction, or neutral.
Freeze ten English pairs before loading the model: four entailments, three
contradictions, and three neutral examples. Use the pinned 82.1M-parameter
`cross-encoder/nli-MiniLM2-L6-H768` with no examples, fine-tuning, threshold
calibration, or generated text. The largest of its three logits is the answer.

The development gate requires at least 9/10 overall, at least 3/4 entailments,
and all three contradictions and all three neutral cases. The run scored 7/10:
3/4 entailments, 2/3 contradictions, and 2/3 neutral cases. It missed a
technical paraphrase, treated one indirectly opposing action as neutral, and
treated one unrelated recommendation as contradiction. The gate failed.

This result says the specialised classifier is more informative than prompt
button wording, but it is not reliable enough to accept or reject incoming
evidence by itself. It is a tiny synthetic English development test, not a
phone, multilingual, or general evidence benchmark. Result:
`site/experiments/E007/nli-minilm-result-v0.1.json`.

## Checkpoint 3C.6O — stronger DeBERTa NLI comparison

Run the already opened ten English source-claim pairs through the pinned
184M-parameter `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli`, without examples,
fine-tuning, or calibration. This model was trained on MNLI, FEVER-NLI, and
ANLI. It must beat MiniLM's 7/10 and satisfy the unchanged 9/10 class-aware
gate. Because the cases and baseline answers are already public, this is a
comparative development check rather than fresh generalisation evidence.

DeBERTa scored 8/10 and failed the locked gate. It fixed MiniLM's missed
indirect contradiction and its false contradiction on the grow-lamp example,
but changed a correct neutral badge-policy example into contradiction. Both
models classified the technical idempotency paraphrase as neutral rather than
entailed. A larger off-the-shelf NLI classifier helped by one point, but did
not make this gate safe enough for automatic evidence acceptance. Result:
`site/experiments/E007/nli-deberta-result-v0.1.json`.

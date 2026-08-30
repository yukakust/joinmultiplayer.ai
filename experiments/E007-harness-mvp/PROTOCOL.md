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

## Checkpoint 3C.6P — twenty fresh short NLI pairs

Before inference, write twenty new synthetic English source-claim pairs with a
human reason for every gold label: seven entailments, seven contradictions,
and six neutral pairs. Include both direct statements and professional
paraphrases such as a repeated payment request ID being an idempotency key.
Run the same pinned DeBERTa once with no examples, training, or calibration.
The locked gate is at least 18/20 overall, at least 6/7 entailments, all seven
contradictions, and at least 5/6 neutral cases.

DeBERTa classified all 20/20 pairs correctly and passed every class gate. A
manual post-run audit agreed with every frozen label and every model decision.
Confidence ranged from 54.4% on emergency-message queue priority to 100.0% on
discarding stale query plans. The fresh idempotency paraphrase was correctly
entailed at 93.7%. This is encouraging synthetic development evidence, not an
independent benchmark or general reliability proof. Result:
`site/experiments/E007/nli-fresh20-short-result-v0.1.json`.

## Checkpoint 3C.6Q — the same twenty with a context package

After the short 20/20 result is known, keep every evidence sentence, claim,
and gold label unchanged. Add a user question plus several surrounding source
sentences. Manually audit each addition before inference so it neither proves
nor reverses the frozen claim. This deliberately tests the combined input
shape currently tempting for the harness; it does not isolate the user question
from surrounding source text. The locked gate permits at most a two-point drop
and keeps the same class requirements as the short test.

The combined context package scored 15/20 and failed the gate, dropping five
points. All five decisions changed from correct to incorrect: three
entailments, one contradiction, and one neutral pair. A manual post-run audit
confirmed that the original evidence and all gold labels remained valid. The
bridge example is especially revealing: the user question repeated the phrase
about forty-tonne vehicles, and the model incorrectly treated that lexical
overlap as source support even though the evidence discussed paint only.

The result does not show that all context is harmful because two variables
changed together. It does show that placing the user question and surrounding
text together inside the NLI premise is unsafe. Result:
`site/experiments/E007/nli-fresh20-context-result-v0.1.json`.

## Gate 15A — complete modular pipeline with Qwen3-1.7B

Freeze the existing E007 world of 64 logical pocket i, 422 separate records,
and all 30 English questions. Run the accepted modules in order: unchanged
question, top-16 public-card routing, owner-local recall-first search, secret
redaction, Qwen3-Reranker-4B relevance, deterministic source anchoring,
Qwen3-1.7B claim writing, DeBERTa source support, lineage storage, meaning
piles, and Qwen3-1.7B closed-world synthesis. Do not train any model and do not
start the application before the owner sees the result.

The locked run failed. Routing and local search found every required owner and
source in 30/30 questions. No synthetic secret leaked, no accepted source
anchor was broken, and no source-unsupported claim entered the evidence board.
But the reranker sent 332 of 480 passages forward as `NOT SURE`. Later modules
proved that many statements were true in their own records without proving
that those records described the device and conditions in the user question.
The final answers therefore mixed in correct but irrelevant knowledge.

Manual semantic review found 10/30 completely correct answers, below the
locked 24/30 gate. It preserved the supported minority in 2/6 cases and the
required uncertainty plus next step in 3/6 cases, both below their 5/6 gates.
The result is a preserved synthetic development failure. The next experiment
must test an explicit question-to-source identity and condition gate before
claim generation; application work remains paused.

Post-run stage audit separates the failure instead of blaming the final model.
Steps 1–4 passed: unchanged questions, required-owner routing, required-source
local recall, and secret redaction. Step 5 was the first break: it retained all
60 required passages but also 345 of 420 extra passages. Step 6 was the second
break: only 34 of 60 required source claims survived because the claim writer
expanded exact evidence and the source NLI checker rejected the expansion.
Only 9 of 30 questions therefore reached piling with both required sources.
Steps 7 and 8 received damaged input and are not isolated by this run.

## Gate 15B — Qwen3-1.7B as a direct relevance gate

Before inference, freeze the same 480 question-fragment pairs opened by Gate
15A. Ask the pinned `Qwen/Qwen3-1.7B` once per pair to return exactly `USEFUL`
or `NOT_USEFUL`. Do not add examples, train, tune a threshold, or run any later
harness stage. Pass only if at least 57/60 required fragments survive, no more
than 42/420 extra fragments survive, and every output is parseable.

The locked run failed. Qwen3-1.7B retained 53/60 required fragments and passed
47/420 extras. It reduced the earlier recall-first reranker's flood from 345 to
47 extras, but lost seven conditional safety rules that become useful only
when combined with a separate cause fragment. All 480 outputs were parseable.

Manual review found a second problem in the test contract. Twenty-nine extra
passes were clearly unrelated. The other eighteen were copied reports about
the exact same case: redundant and not required, but reasonably related to the
question's disputed view. The frozen score is not changed after seeing this.
The result therefore rejects this binary gate while showing that the next test
must distinguish a missing answer slot, truly unrelated evidence, same-case
redundancy, and condition mismatch. Protocol, raw decisions, and audit:

- `site/experiments/E007/qwen17b-relevance-protocol-v0.1.json`
- `site/experiments/E007/qwen17b-relevance-result-v0.1.json`
- `site/experiments/E007/qwen17b-relevance-human-audit-v0.1.json`

## Gate 15C — server-side Qwen3-8B relevance comparison

Freeze a paired comparison before downloading or running the model. Reuse the
same 480 pairs, prompt, strict parser, greedy non-thinking generation, and
57/60 recall plus 42/420 extra-pass thresholds from Gate 15B. Change only the
model from pinned Qwen3-1.7B to pinned Qwen3-8B in BF16 on yukabox. Run once
without examples, training, prompt edits, threshold tuning, or later stages.

The locked run failed. Qwen3-8B retained 41/60 required fragments and passed
18/420 mechanically extra fragments. It therefore reduced the extra set again
but lost nineteen required pieces, versus seven for 1.7B. All outputs parsed.

Manual review found a clean semantic pattern. All nineteen losses were useful:
fifteen conditional safety rules and four instructions for the next missing
measurement. All eighteen passed extras were copied reports about the exact
same device and symptom; no clearly foreign device or generic background note
survived. The larger model interpreted `directly helps` more strictly. It kept
single-fragment diagnoses while rejecting pieces that become useful through
composition with another fragment.

Do not install this 8B binary decision as the server relevance gate. More model
parameters traded recall for precision and did not repair the contract. The
next test should name the missing answer slot—cause, safe action, or next
evidence—and measure unrelated, same-case redundant, and condition-mismatch
fragments separately. Protocol, raw trace, and manual audit:

- `site/experiments/E007/qwen8b-relevance-protocol-v0.1.json`
- `site/experiments/E007/qwen8b-relevance-result-v0.1.json`
- `site/experiments/E007/qwen8b-relevance-human-audit-v0.1.json`

## Gate 15D — Qwen3-8B sees each whole evidence bundle

Freeze the same 480 fragments as thirty case folders with sixteen fragments
each. Before the run, broaden relevant gold beyond the sixty required pieces:
six condition-mismatch look-alikes and eighteen dependent copied reports are
same-case alternatives, for 24 alternatives and 396 irrelevant records.

Run two sequential Qwen3-8B calls per folder without training or examples.
First, select direct evidence, conditionally useful rules, and competing views
from all sixteen fragments together. Second, synthesize a JSON answer containing
the best-supported view, cited evidence IDs, an alternative view, the safe
action or next measurement, citations, and uncertainty. Manually score all
thirty final answers; exact strings are not the judge.

The locked selector found all 30 core pieces and all 30 conditional action or
next-measurement pieces, while retaining 0/396 frozen irrelevant fragments.
This completely repaired the pairwise X-to-Y composition failure. However, it
also discarded all 24 same-case alternatives despite an explicit instruction
to preserve them, so the selector gate failed.

Manual review found the best-supported cause or explicit uncertainty and the
safe action or next measurement correct in all 30/30 answers. Only 16/30 passed
the complete rubric. All twelve tasks requiring a competing view failed because
its source had already been removed; the writer then omitted it or cited the
opposing source as support. Q11, Q19, and Q30 added three unsupported generic
alternatives. No foreign-device fact, synthetic secret, parse failure, or token
limit occurred. Runtime on yukabox CPU BF16 was 1,297.745 seconds.

The whole-bundle view is accepted as a successful repair for composition and
clear-junk removal, but Gate 15D is rejected as a complete evidence-preserving
harness. Separate the jobs next: mechanically retain same-case alternatives
and lineage on one shelf, while Qwen builds the best-supported answer on a
second shelf. The writer receives both and may not cite one view's source as
evidence for the other. Protocol, trace, and audit:

- `site/experiments/E007/qwen8b-bundle-protocol-v0.1.json`
- `site/experiments/E007/qwen8b-bundle-result-v0.1.json`
- `site/experiments/E007/qwen8b-bundle-human-audit-v0.1.json`

## Accepted architecture after Gate 15D — immutable ledger, two views

Owner decision on 2026-08-29: preserve every consented incoming capsule in an
append-only question ledger after permission, secret, source-anchor, and
envelope checks. A model may choose what to use, but it may not decide what
ceases to exist.

Expose two primary views over the same ledger. `best_answer` contains the
strongest supported answer and its own citations. `all_versions` preserves
same-case alternatives, conditional rules, sources, and lineage. UI shelves are
`USED`, `SAME_CASE`, `CONDITIONAL`, `UNCERTAIN`, and collapsed `OTHER`. Copies
sharing one lineage count as one dependent view.

This combines the observed strengths rather than intersecting their outputs:
Gate 15D found all sixty required cause/action pieces; Gate 15C retained the
same-case copied reports that best-answer optimization removed. Neither model
view is allowed to erase the original capsule. Decision record:
`site/experiments/E007/evidence-ledger-accepted-architecture-v0.1.json`.

Next, Gate 15E deterministically constructs both shelves from the preserved
15C and 15D traces, with no new inference. Gate 15F may test a final writer only
after the ledger retains all required pieces, alternatives, and lineage without
putting foreign records in the visible shelves.

## Gate 15E — locked two-shelf mechanics

Gate 15E calls no model. It first stores all 480 received fragments. `USED` is
the unchanged Gate 15D selection. `SAME_CASE` uses only frozen sender metadata:
the card and task contract agree (`lookalike` for a condition-mismatch task or
`dependent-copy` for a copied-report dispute), and the named object from the
question occurs in the fragment. `CONDITIONAL` is a badge on selected safety or
next-measurement rules. Everything else is `OTHER`: hidden by default, never
deleted. Records sharing one lineage become one visible dependent view while
their originals remain in the ledger.

Expected answers and frozen gold may score the completed build but may not
choose shelves. This is a synthetic development mechanics test. It trusts the
sender-declared tags and does not yet test an unseen sender, dishonest metadata,
or a final writer. Locked machine-readable protocol:
`site/experiments/E007/evidence-ledger-protocol-v0.1.json`.

Gate 15E result: passed all frozen mechanics gates without a model call. The
append-only ledger contains all 480/480 records. The `USED` view contains all
60/60 required pieces. `SAME_CASE` contains all 24/24 frozen alternatives. The
remaining 396 records are preserved and hidden by default. Eighteen copied
records collapse into six dependent lineage views without deleting their
originals. This validates the deterministic storage/view mechanism only; it
does not validate sender tags, unseen questions, or the final writer. Result:
`site/experiments/E007/evidence-ledger-result-v0.1.json`.

## Gate 15F — locked USED-shelf writer

Gate 15F gives Qwen3-8B only the thirty questions and sixty fragments already
placed on `USED` by Gate 15E. The model cannot see `SAME_CASE` or `OTHER`. It
must write one short natural answer containing the supported cause or explicit
uncertainty and the safe action or next measurement, with citations drawn only
from that question's two supplied fragments.

This is not the unseen physical-device test. It isolates one remaining joint:
whether a complete correct shelf can become a complete human answer without
dropping a part or inventing advice. The locked gate requires 30/30 parseable
answers, zero token-limit hits, 30/30 causes or uncertainties, 30/30 actions or
next measurements, zero unsupported additions, and zero alternative leaks.
Manual meaning review is required. Protocol:
`site/experiments/E007/used-shelf-writer-protocol-v0.1.json`.

Gate 15F passed its locked synthetic development gate. Qwen3-8B produced 30/30
parseable answers with no token-limit hits. Manual review found the supported
cause or explicit uncertainty in 30/30, the safe action or next measurement in
30/30, both supplied source IDs cited in 30/30, and zero unsupported additions,
alternative-shelf leaks, secret leaks, or truncations. This closes only the
writer-from-correct-shelf joint. The next experiment must use unseen data and
physical devices to test the full chain. Result and audit:

- `site/experiments/E007/used-shelf-writer-result-v0.1.json`
- `site/experiments/E007/used-shelf-writer-human-audit-v0.1.json`

## Gate 16A — locked fresh two-device MVP test

The main remaining MVP question is now frozen before any node search or model
inference: can the complete harness build a correct `USED` shelf from fresh
knowledge transported by physical pocket i? Six new English questions and four
new six-record libraries are split across two real devices. Every answerable
question needs one source from MacBook and one from yukabox. Two cases also have
same-case alternatives, and one question targets a private Mac-only canary that
must be blocked.

Four physical node processes must first return all 72 lane receipts through the
public relay. Only then may the locked central pipeline verify sources, run the
accepted relevance and NLI modules, build the immutable ledger and shelves, and
write the main answer from `USED` only. Protocol and fresh test memory:

- `site/experiments/E007/physical-mvp-protocol-v0.1.json`
- `site/experiments/E007/physical-mvp-memory-v0.1.json`

This remains synthetic and uses two devices owned by one person. It is the
first complete physical transport test, not a privacy proof, distributed neural
inference, or evidence about internet scale.

Gate 16A failed and is preserved without a retry. Physical transport passed:
4/4 nodes on MacBook and yukabox returned 72/72 terminal receipts, and the raw
private canary never left the MacBook. Nine of ten required public sources
reached the verified candidate ledger, and four of five ordinary questions
received a complete correct answer.

`P04` failed because local MacBook search never offered `M2-DARO-SAFE`; later
stages could not recover that missing half. `P06` failed even though the private
record was blocked: the shelf builder mistook a public C4 safety instruction
for the requested private code, and the writer repeated that unsupported
inference. Qwen also misplaced several irrelevant or competing records between
`USED`, `SAME_CASE`, and `OTHER` without always contaminating the final answer.
Cross-device composition is real, but local recall and closed-world shelf
construction remain unsafe failure points. Result and manual audit:

- `site/experiments/E007/physical-mvp-result-v0.1.json`
- `site/experiments/E007/physical-mvp-human-audit-v0.1.json`
- `site/experiments/E007/physical-mvp-answer-review-v0.1.json`

## Gate 16B.1 — whole cleaned conversations before retrieval

Before building message-level search, Gate 16B.1 asks whether Qwen3-8B can read
two complete cleaned Codex child-agent conversations in its native context.
The inputs contain visible user and assistant messages only. Reasoning, tool
traffic, system/developer messages, and automatically supplied plugin catalogues
are excluded. No RAG, chunking, summary, training, examples, or location hints
are used. Each conversation is read once with three questions spanning its
early, middle, and late messages; the same questions are also asked without the
conversation as a control.

The first development attempt is preserved but invalid: after a size-preflight
replacement, two questions accidentally still referred to the prior CHAT-A.
They are not scored. Protocol v0.2 corrected the fixture before its inference
and reran both conversations unchanged.

The valid development result passed its locked narrow gate. The conversations
contained 10,656 and 12,922 Qwen tokens. Qwen recovered all six facts and cited
the correct supporting message for five, for 11/12 points. Without either chat
it returned `NOT_FOUND` for all six, for 0/12. The two full-context CPU calls
took 692.489 seconds in total. This supports whole-chat reading around 10k–13k
tokens; it does not validate library search, main user chats, unrelated domains,
or conversations beyond the context window. Raw private conversations and
session IDs are not published.

- `site/experiments/E007/whole-chat-reader-protocol-v0.2.json`
- `site/experiments/E007/whole-chat-reader-result-v0.2.json`

## Gate 16B.2 — reuse one exact conversation KV-cache

Gate 16B.2 prefills the unchanged 10,750-token CHAT-A prefix once with
Qwen3-8B BF16 on yukabox CPU. Two different questions branch from deep copies
of that same immutable `past_key_values`; neither branch rereads the chat.

The cache mechanism worked, but the strict development gate failed. Prefill
took 137.608 seconds. The first question cost 221.401 seconds including prefill;
the second cached question cost 83.993 seconds, a 2.636x first-use speedup. Cache
cloning itself took under 0.15 seconds. Both facts were correct, but both source
IDs copied the prompt's literal `M0000` placeholder, so source quality was 0/2.
The cached answer also missed the locked quarter-time target.

The measured BF16 cache was 1,585,152,000 bytes (1.476288 GiB). This is not the
text: every token stores K and V tensors across 36 layers, 8 KV heads, and 128
dimensions. After prefill, the dominant bottleneck was CPU generation at about
1.4 output tokens per second. Next speed work must test an optimized quantized
runtime and shorter outputs; cache reuse alone is insufficient.

- `site/experiments/E007/kv-cache-reuse-protocol-v0.1.json`
- `site/experiments/E007/kv-cache-reuse-result-v0.1.json`

## Gate 16B.3 — Q8 versus Q4 KV cache

Gate 16B.3 separates two kinds of four-bit compression. The Qwen3-8B model
weights are held fixed at `Q4_K_M`; only the memory of the already-read tokens
changes from `Q8_0` to `Q4_0`. Both lanes receive the same two private cleaned
conversations and the same six questions from Gate 16B.1. The public result may
contain the questions, model answers, manual scores, timings, and runtime memory
measurements, but never the source conversations.

The cache-only quality gate allows Q4 KV to lose at most one point out of 12
against Q8 KV and forbids degenerate output. Speed is reported separately:
Q4 KV primarily saves cache memory, while the older BF16 Transformers result is
used only as a non-causal engineering reference for the whole optimized stack.

Locked protocol:

- `site/experiments/E007/kv-cache-quantization-protocol-v0.1.json`

The first development run was invalid because its format example contained a
fake answer and fake evidence ID that both lanes copied. It is preserved rather
than scored. The corrected protocol removes all example values:

- `site/experiments/E007/kv-cache-quantization-invalid-attempt-v0.1.json`
- `site/experiments/E007/kv-cache-quantization-protocol-v0.2.json`

The corrected three-answer JSON run was valid but both lanes hit a quality
floor, so it could not cleanly compare cache precision. It remains public. A
third locked protocol removes JSON and asks each of the six questions
individually with at most 128 generated tokens:

- `site/experiments/E007/kv-cache-quantization-floor-attempt-v0.2.json`
- `site/experiments/E007/kv-cache-quantization-protocol-v0.3.json`

Development result: Q4 KV reduced the one-slot 16,384-token buffer from 1,224
MiB to 648 MiB, but scored 1/6 versus 2/6 for Q8 and produced one degenerate
answer. Both lanes were weak on the difficult long-conversation task, so this
does not estimate a general average loss. It is enough to reject Q4 KV as the
default for the MVP. Q8 remains the default; Q4 is an explicit low-memory mode.
The optimized Q4-weight ROCm stack generated roughly 9–10 tokens/s, versus
about 1.4 tokens/s in the prior BF16 CPU run. The big speed gain came from the
weight/runtime change, not from Q4 KV itself.

- `site/experiments/E007/kv-cache-quantization-result-v0.3.json`

## Gate 16B.4 — exact BF16 weights on the integrated Radeon

Gate 16B.4 keeps the unquantized BF16 Qwen3-8B weights and Q8 KV cache, but
moves every transformer layer from CPU execution to the integrated Radeon via
ROCm. It reuses the exact Gate 16B.1 conversations, six questions, and grouped
prompt. The prior BF16 CPU run is the locked reference: 11/12 and roughly 1.4
generated tokens per second. Success requires all layers on ROCm, at least
11/12, and throughput above 1.4 tokens/s.

- `site/experiments/E007/bf16-rocm-protocol-v0.1.json`

The ready-made BF16 GGUF did not preserve the behavior of the checkpoint used
by Gate 16B.1. Its two launch attempts are retained as diagnostic failures, not
scored as a CPU-versus-Radeon comparison. Protocol v0.2 instead converts the
exact cached Hugging Face revision from Gate 16B.1 without weight quantization:

- `site/experiments/E007/bf16-rocm-protocol-v0.2.json`

Development result: all 37/37 layers fit on ROCm and generation rose from about
1.4 to 3.9 tokens/s, but the manual long-context score fell from 11/12 to 3/12.
The optimized path is rejected for the MVP until the runtime quality gap is
understood. All six questions and answers are published for visual review.

- `site/experiments/E007/bf16-rocm-result-v0.2.json`

## Gate 16B.5 — one llama.cpp file, CPU versus Radeon

Gate 16B.5 holds the exact BF16 GGUF, llama.cpp build, native template, Q8 KV,
reasoning-off setting, conversations, questions, and prompt constant. Only the
execution device changes. If CPU and ROCm fail similarly, investigate the
shared llama.cpp path. If CPU recovers the 11/12 reference while ROCm remains
poor, investigate the ROCm device path.

- `site/experiments/E007/llamacpp-cpu-rocm-protocol-v0.1.json`

## Gate 16B.5 — same GGUF on CPU and Radeon

The locked device-pair test is complete. The exact BF16 GGUF and the same
`llama-server` build scored 11/12 on CPU and 1/12 on the integrated Radeon.
This rules against a general GGUF conversion or shared llama.cpp failure for
these prompts and localizes the observed quality loss to the Radeon/ROCm path.
It does not yet identify the faulty GPU operation. Public result:
`/experiments/E007/llamacpp-cpu-rocm-result-v0.1.json`.

## Gate 16C — local sender extraction from real conversations

Before inference, Gate 16C freezes two previously unused allowlisted Codex
conversation files and ten questions: five supported and five close but absent
controls. Qwen3-8B on CPU sees one cleaned conversation and five questions at a
time. It must return either `FOUND` with one short claim and exact visible
message IDs, or `EMPTY`. Ordinary code then rehydrates the named messages from
the immutable local JSONL. Raw conversations, session IDs, and raw model output
stay private. This tests extraction from an already selected conversation, not
search across the full local library.

- `/experiments/E007/sender-extraction-protocol-v0.1.json`

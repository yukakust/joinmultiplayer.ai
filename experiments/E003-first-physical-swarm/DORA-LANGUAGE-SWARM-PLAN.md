# E004 plan — Architecture Arena for a growing pocket i swarm

Status: `CHECKPOINT 1 REBUILDING · NO MODEL DOWNLOADED · NO TRAINING`

## Question

> Does accessible knowledge and solution quality grow as 1, 2, 4, and 8
> independent pocket i join one temporary distributed neural network, while a
> new pocket i can join without retraining the central system?

The swarm is allowed to use more total private data, parameters, and compute as
it grows. That scaling advantage is the hypothesis, not a confound to remove.
Equal-compute, equal-byte, and equal-latency comparisons remain diagnostic
controls: they explain the gain but are not the project's final objective.

Passing E004 would support only a synthetic mechanism on one host. It would not
prove useful personal AI, internet latency, privacy, security, or billion-device
scaling.

## One parallel pass

E004 excludes repeated rounds of agent conversation:

```text
question -> select relevant pocket i
         -> all selected i compute in parallel
         -> each returns one complete contribution
         -> source i fuses the completed contributions
         -> answer
```

For token-level MoE, selected experts fan out in parallel once per generated
token. Autoregressive tokens remain sequential, but there are no additional
whole-answer debate rounds.

## The two questions inside the arena

### A. How does one pocket i keep unique knowledge?

Every method receives the same private book:

1. **Local RAG** — exact, inspectable, mutable records; no weight training.
2. **DoRA** — parameter-efficient supervised fine-tuning of personal weights.
3. **Partial/full fine-tuning** — a capacity control for DoRA, promoted only if
   the hardware smoke is practical.
4. **Trainable neural memory** — sparse learned key/value capacity.
5. **Hybrid** — DoRA for procedures plus neural memory and RAG for exact facts.

The shared Qwen lineage supplies language. Personal training and memory create
the differences. DoRA is a candidate, not the assumed winner.

### B. How do several pocket i become one temporary network?

The arena compares five single-pass interfaces:

1. **RAG swarm** — pockets return evidence records; the source synthesizes.
2. **Memory-token swarm** — pockets return a fixed number of learned memory
   tokens; the source cross-attends to them once.
3. **Latent-delta towers** — pockets return bounded residuals relative to the
   shared base representation.
4. **Personal token-MoE** — remote personal FFN experts are selected and fused
   for each token.
5. **DoRA adapter assembly** — selected personal adapters temporarily form a
   larger local sparse model at the source.

A hybrid of the strongest storage and composition methods is evaluated only
after the component tournament. Recurrent multi-round deliberation is excluded.

## The synthetic population

A deterministic generator creates disjoint fictional books:

- `S01..S16`: surrogate pocket i used to train routers and mergers;
- `I01..I08`: final pocket i never seen during central training;
- `I09`: a new pocket i attached only after the central system is frozen;
- a separate public seed: readable examples that never enter evaluation.

Each book contains:

- 256 unique exact facts;
- 256 examples of one stable local procedure;
- 64 updates or deletions that supersede older facts;
- paraphrased questions and deterministic answers.

Splits are disjoint by entities and rules, not merely by prompt wording. Test
questions use unseen combinations. The central router/merger never receives the
final pockets' books, labels, retrieval indexes, or personal weights.

The task families are:

1. retrieve knowledge held by one pocket;
2. compose knowledge held by two or three pockets;
3. apply a learned procedure to a new example;
4. honor an update or deletion instead of repeating stale knowledge;
5. abstain when the required pocket is absent.

Answers use large structured spaces. Binary answers are forbidden as the main
metric.

## Shared base and controls

The initial shared lineage remains `Qwen/Qwen3-0.6B-Base` at the already pinned
revision. The first arena keeps all pocket models at the full compatible depth;
`6/12/24` elastic branches are postponed because depth is not the present
question.

Required controls:

- frozen Qwen 0.6B alone;
- best single pocket and every relevant pair;
- text and logit ensembles;
- one central 0.6B trained on the union of allowed lessons;
- Qwen 1.7B as a larger dense reference when the smoke confirms the run fits;
- exact relevant-data RAG;
- missing, irrelevant, duplicate, stale, and malformed pocket contributions;
- swarm sizes `N = 1, 2, 4, 8`, followed by unseen `I09`.

The 1.7B reference is a ruler, not a pass condition. E004 asks whether accessible
unique capacity grows with owners, not whether three 0.6B models literally
become one dense 1.8B checkpoint.

## Training boundary

No model is trained before Checkpoint 1 approval.

After approval:

1. pin the environment, model files, tokenizer, code, and checksums;
2. benchmark one inference and one gradient step on CPU and any verified AMD
   path;
3. run a two-surrogate smoke for each storage method;
4. publish before/after evidence and stop for owner review;
5. train surrogate pockets and the candidate routers/mergers;
6. freeze central components and all thresholds;
7. create/train final `I01..I08` independently;
8. run the locked scaling evaluation once on multiple frozen seeds;
9. attach `I09` without central retraining and evaluate again.

RAG indexing is not weight training. DoRA, partial/full fine-tuning, neural
memory, routers, mergers, and MoE experts all use real gradient updates and must
publish declared trainable parameter groups plus frozen-weight hash checks.

## Pre-registered success conditions

At least one architecture must satisfy all of these on locked seeds:

- every trained pocket reaches at least 90% on its local held-out procedure;
- correct accessible unique items at `N=8` reach at least 75% of ideal linear
  growth from `N=1`;
- full-swarm exact match on multi-pocket tasks beats the strongest single or
  relevant pair by at least 20 percentage points;
- adding irrelevant or duplicate pockets changes exact-match accuracy by no
  more than 5 percentage points;
- removing a required pocket causes at least a 15-point loss or a correct
  abstention rather than a fabricated complete answer;
- unseen `I09` reaches within 10 points of comparable existing pockets without
  central retraining;
- private final books cannot be reconstructed from public artifacts or appear
  in central training inputs;
- failures, exact-RAG wins, and negative architecture results remain visible.

Fact retrieval and procedural transfer are reported separately. If learned
weights do not improve procedural tasks beyond exact RAG, the result does not
justify neural personalization.

## Non-negotiable owner-visible evidence rule

Every meaningful step produces something the owner can inspect before work
silently moves on. Prefer the public E004 page on `joinmultiplayer.ai`; if a safe
site snapshot is not ready, show it in Codex first and publish the reviewed
snapshot next.

Every visible stage answers:

1. What changed?
2. What can be inspected: examples, before/after outputs, diagram, table,
   curve, or downloadable artifact?
3. Which metric, failure, or uncertainty appeared?
4. What is the proposed next step?

Small mechanical actions may be grouped. Environment validation, data locking,
every distinct training method, merger training, architecture selection, and
locked evaluation may not be hidden inside a later summary. Public evidence is
redacted and never exposes private lessons, credentials, tokens, raw personal
memory, or unsafe hidden states.

## Three owner checkpoints

### Checkpoint 1 — approve the arena before training

The site shows the hypotheses, five architectures, data-world examples,
controls, success thresholds, hardware window, and explicit non-claims. The
owner may change or approve the design. Nothing is downloaded or trained.

### Checkpoint 2 — review real learning smokes

For each storage method the site shows lessons, before/after outputs, local
held-out score, loss curve, changed parameter groups, base-hash proof, memory
size, elapsed time, and failures. Full arena training waits for owner approval.

### Checkpoint 3 — inspect the locked result

The site shows scaling curves, the complete comparison table, `I09` plug-in
test, limitations, and a microscope for successful and failed tasks. The owner
records `supported in this task world`, `not supported`, or `inconclusive`.

## Yukabox execution window

Heavy experiment jobs may run only from `08:00` to `23:45` in the agreed
Central European local timezone. At `23:45` they checkpoint; by `23:55` they
stop. No E004 training runs between `00:00` and `08:00`.

Initial safe ceiling:

- at most 22 of 24 CPU threads;
- at most 52 of 59 GiB RAM;
- accelerator use only after a measured compatible smoke;
- resumable checkpoints for any job longer than one window.

Before scheduling, record whether the intended clock is `Europe/Berlin`
(including daylight saving) or fixed `CET` (`UTC+1`).

## Public E004 page

`/experiment/?id=E004` must show:

1. question, boundary, current checkpoint, and visible-evidence rule;
2. eight pocket slots plus the unseen plug-in slot;
3. five architecture cards and their honest status;
4. public example books and task derivations;
5. success thresholds and server schedule;
6. after training: learning cards, scale curves, task microscope, failures,
   hashes, JSON/JSONL artifacts, and reproduction commands.

Static reviewed snapshots are sufficient. E004 does not require live loss
streaming, user accounts, or on-site approval buttons.

## Immediate execution order

1. Rewrite the E004 protocol and public shell as Architecture Arena.
2. Implement and test the public deterministic data-world generator.
3. Publish Checkpoint 1 and wait for owner review.
4. Only after explicit approval: prepare the ML environment and run smokes.
5. Stop again at Checkpoint 2 before full training.
6. Run development, freeze, then locked evaluation.
7. Only after Checkpoint 3 choose a winner for phone, Mac, and yukabox.

## Explicitly postponed

- personal human data;
- training on the three physical devices;
- production WAN activation streaming;
- automatic global expert routing;
- account systems;
- continuous autonomous learning;
- billion-device security and Byzantine robustness.

## Method references

- DoRA: <https://arxiv.org/abs/2402.09353>
- CALM model composition: <https://arxiv.org/abs/2401.02412>
- Branch-Train-MiX: <https://arxiv.org/abs/2403.07816>
- Memory Layers at Scale: <https://arxiv.org/abs/2412.09764>

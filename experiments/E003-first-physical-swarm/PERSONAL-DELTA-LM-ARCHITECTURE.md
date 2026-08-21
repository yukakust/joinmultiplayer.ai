# Personal Delta LM — reuse boundary and architecture decision

Status: **pre-experiment architecture decision; no model has been trained**  
Date: **2026-08-21**  
Source hypothesis: **H0001**  
Execution target for the first feasibility study: **yukabox**

## Decision

There is no known downloadable language model that already implements the
complete intended system:

```text
one shared language path
+ personal owner-trained branches of different depths
+ branches executing in parallel on unrelated consumer devices
+ delta relative to a matching base branch
+ one frozen neural ABI
+ bounded latent fusion into shared final layers
+ local memory and owner-controlled continual learning
```

Therefore we will not search for a mythical ready-made pocket i. We will reuse
an open pretrained language model for language competence and build the
personal-branch architecture around it.

What we reuse:

- tokenizer, embeddings, and pretrained language representations;
- transformer blocks and pretrained weights;
- local fine-tuning and adapter tooling;
- quantization and device runtimes;
- known approaches to elastic depth, distributed execution, modular experts,
  and representation composition.

What remains new and must be tested:

- subtraction of a personal depth-specific path from its matching base path;
- a versioned neural ABI shared by 6-, 12-, and 24-block branches;
- bounded fusion of several independently personalized deltas;
- plug-in branches that continue learning locally without drifting out of the
  ABI;
- one autoregressive answer whose temporary neural graph crosses the phone,
  Mac, and server;
- routing and transactional removal of incomplete remote contributions;
- privacy and adversarial safety for transmitted hidden representations.

This is a new composition of established ingredients, not a claim that every
ingredient is new.

## Closest primary work — and the gap that remains

### Petals — WAN transformer execution

[Petals](https://arxiv.org/abs/2312.08361) demonstrates distributed inference
and fine-tuning of very large language models over consumer-grade networks. It
addresses heterogeneous devices, disconnects, load balancing, and hidden-state
transmission.

What it gives us:

- evidence that hidden activations and KV-dependent transformer work can cross
  a real WAN;
- failure recovery and replay ideas;
- a practical distributed runtime precedent.

What it does not give us:

- parallel personal branches contributing simultaneously;
- owner-specific independently trained weights;
- a personal delta relative to a common base;
- 6/12/24 elastic branches fused by a shared merger.

Petals mainly partitions one model's sequential blocks across machines. Pocket
i proposes several personal paths in parallel.

### DiPaCo — modular paths on weakly connected workers

[DiPaCo](https://arxiv.org/abs/2403.10616) co-designs transformer modules and
training paths for heterogeneous, poorly connected compute. It shows that many
paths can be trained with infrequent synchronization and tolerate worker
failures.

What it gives us:

- a credible modular-training precedent;
- path-level rather than token-level expert selection;
- reduced communication during distributed training.

What it does not give us:

- parallel fusion of several paths at inference;
- personal owner-controlled continual learning;
- latent delta composition. At inference DiPaCo chooses one path per input.

### CALM and BTS — representation composition and stitching

[CALM](https://arxiv.org/abs/2401.02412) composes a frozen anchor language model
with a specialized model through learned cross-attention over intermediate
representations.

[Branch-Train-Stitch](https://arxiv.org/abs/2502.00075) combines independently
trained frozen experts with a seed model using lightweight stitch layers.

What they give us:

- evidence that independently specialized model representations can be
  integrated without destroying the source models;
- learned projection/cross-attention as a more defensible bridge than directly
  concatenating arbitrary hidden states;
- a basis for versioned ingress and egress projections.

What they do not give us:

- billions of private branches joining over a WAN;
- local continual learning after deployment;
- our base-relative delta and strict contribution budget;
- a phone/Mac/server autoregressive runtime.

### Branch-Train-MiX — one seed becomes specialized experts

[Branch-Train-MiX](https://arxiv.org/abs/2403.07816) starts from one seed model,
trains domain experts independently, and then mixes their feed-forward weights
into a centrally fine-tuned MoE.

What it gives us:

- evidence that a shared initialization need not create permanent monoculture;
- independent specialist training from one seed;
- a useful control for whether our branches develop real specialization.

What it does not give us:

- experts remaining on their owners' devices;
- deep personal tracks returning bounded deltas;
- dynamic WAN composition without centralizing the expert weights.

### LayerDrop — several depths from one lineage

[LayerDrop](https://arxiv.org/abs/1909.11556) trains a transformer with structured
layer dropout so sub-networks of different depths can be extracted with limited
quality loss.

What it gives us:

- a direct precedent for an elastic-depth family;
- a training technique for making depth reduction deliberate rather than
  deleting arbitrary layers after training.

What it does not give us:

- a common neural ABI between differently personalized depths;
- parallel fusion;
- local owner-specific training.

### PEER — very many experts

[PEER](https://arxiv.org/abs/2407.04153) shows sparse routing among more than a
million tiny experts.

What it gives us:

- evidence that expert-count scale and sparse selection are compatible;
- product-key routing ideas for a later large network.

What it does not give us:

- deep personal branches;
- experts on unreliable owner devices;
- private local memory or owner identity.

## Proposed first architecture

The first single-host language-model feasibility study uses one small pinned
open decoder model and three isolated personal branches.

```text
tokens
  |
shared frozen tokenizer + embedding + stem
  |
  +--------------------------------------------------> trusted z0
  |
  +-> Base6  / Personal6  -> raw delta6  -> FrozenProjection6  --+
  +-> Base12 / Personal12 -> raw delta12 -> FrozenProjection12 -+--> bounded merge
  +-> Base24 / Personal24 -> raw delta24 -> FrozenProjection24 -+          |
                                                                          v
                                                     FinalLayers(z0 + update)
                                                                          |
                                                                        logits
```

For depth `d`:

```text
raw_delta_i = PersonalTower_i,d(Pin_d(h), local_state_i)
              - BaseTower_d(Pin_d(h))

delta_i = Clip(
            Normalize(
              Pout_d(raw_delta_i)
            ),
            per_expert_norm_budget
          )

update = PermutationAwareMerge(h, {delta_i, identity_i, lineage_i,
                                    confidence_i, abstain_i})

logits = LMHead(FinalLayers(z0 + update))
```

The matching base reference is essential. A 6-block personal path is compared
with its 6-block base path, not directly with the 24-block teacher. Every depth
then projects its difference into the same ABI space.

## Why a ready pretrained model is still useful

The starting checkpoint does not need to contain parallel tracks. It supplies
the costly part we do not want to relearn in the first experiment: tokenization,
syntax, semantics, common world patterns, and ordinary language generation.

The feasibility study adds:

1. depth-specific base references;
2. personal copies or adapters;
3. learned frozen ingress/egress projections;
4. a bounded set-aware merger;
5. isolation, training, and evaluation boundaries.

This is analogous to using a pretrained vision backbone when testing a new
multi-camera fusion architecture: the backbone need not already contain the
cameras.

## How to obtain 6-, 12-, and 24-block paths

Do not simply retain every fourth layer and call the result compatible.

The first development sequence is:

1. Choose a teacher lineage with enough blocks and an inspectable architecture.
2. Freeze a canonical stem, latent width, normalization convention, and final
   language path.
3. Construct 24-, 12-, and 6-block students from the same lineage.
4. Distill next-token distributions and selected hidden representations from
   the teacher while sampling depths.
5. Train one small projection per depth into a canonical ABI dimension.
6. Verify ordinary language behavior and ABI alignment on held-out public text.
7. Clone every depth-specific base into a personal branch.
8. Assert numerically that every fresh personal branch returns delta near zero.
9. Freeze the projections and common path before personal learning.

For the phone alpha, a short tower plus adapter is the likely first target. The
experiment must report adapter training as adapter training. Full continual
training of six transformer blocks on the phone is a later hardware result, not
an assumption.

## Local learning contract

Personal learning changes only declared owner parameters. The common model,
neural ABI, and final path remain frozen in the first study.

```text
mutable exact fact      -> local inspectable memory / RAG
stable personal skill   -> local adapter or personal middle blocks
shared language ability -> frozen pretrained base
```

Every owner process has:

- its own training shard;
- its own optimizer and checkpoint directory;
- a local held-out set;
- before/after general-language regression;
- declared trainable parameter names;
- weight delta norm and checksum;
- a promote-or-rollback decision;
- an abstention calibration set.

No owner data enters merger training or another branch.

## First experiment boundary

The first experiment is not yet a network-speed test. All three branches run
in isolated processes on yukabox so we can falsify the neural mechanism before
adding phones, networks, quantization differences, and disconnects.

The mechanism advances only if:

- fresh deltas are near zero;
- three depths satisfy the same frozen ABI;
- each personal branch learns only its assigned component;
- no single branch or pair solves a locked three-way task;
- the full set solves held-out compositions;
- removing `z0` measurably hurts tasks requiring common language competence;
- exact RAG does not explain away the claimed procedural/capability result;
- incomplete or malformed contributions are rejected before fusion;
- the full path is visible in a human-readable microscope.

Only after that do we deploy inference-only branches to the phone, Mac, and
yukabox. Only after hardware compatibility do we enable local physical-device
training.

## The honest answer

The owner is correct: no existing open checkpoint appears to provide this whole
architecture ready to run. The closest work proves separate pieces. Our next
experiment is valuable precisely because it asks whether those pieces can be
combined into one coherent language model.

The correct first move is therefore:

```text
reuse a small open pretrained language model
+ implement one-host Personal Delta Towers
+ prove or falsify neural composition
+ only then distribute the paths across three devices
```

The full execution plan and safety boundary are in
[`NEXT-LANGUAGE-MODEL-HANDOFF.md`](NEXT-LANGUAGE-MODEL-HANDOFF.md). The Miro
explanation is mirrored in [`POCKET-I-SWARM-MAP.md`](POCKET-I-SWARM-MAP.md).

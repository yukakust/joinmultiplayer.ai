# Checkpoint 1 draft — approve the test before training

Status: `NEEDS OWNER REVIEW · NO TRAINING`

## Owner-visible evidence rule

Every meaningful stage must be shown to the owner, preferably on the public
E004 page, before the experiment silently advances. Each snapshot must show
what changed, inspectable evidence, the observed metric or failure, and the
proposed next step. Private lessons and unsafe raw internals remain private.

## Recommendation

Use `Qwen/Qwen3-0.6B-Base` at revision
`da87bfb608c14b7cf20ba1ce41287e8de496c0cd`.

Why this candidate:

- official Qwen base checkpoint under Apache-2.0;
- 28 transformer blocks, so the proposed `6/12/24` paths fit one lineage;
- 1,192,135,096-byte BF16 safetensors file: small enough for the first study;
- hidden width 1,024 and an inspectable dense architecture;
- base rather than instruction-tuned weights, which avoids mixing personal
  procedure learning with an opaque chat fine-tune;
- multilingual pretraining makes the later Russian UI less artificial, while
  the locked answer remains exact and language-independent.

Pinned metadata:

| Field | Value |
| --- | --- |
| model | `Qwen/Qwen3-0.6B-Base` |
| revision | `da87bfb608c14b7cf20ba1ce41287e8de496c0cd` |
| license | Apache-2.0 |
| model file | `model.safetensors` · 1,192,135,096 bytes |
| layers | 28 |
| hidden / MLP width | 1,024 / 3,072 |
| attention | 16 query heads · 8 KV heads · head dimension 128 |
| context advertised by config | 32,768 tokens |
| dtype | BF16 |

Primary model sources:

- <https://huggingface.co/Qwen/Qwen3-0.6B-Base>
- <https://huggingface.co/Qwen/Qwen3-0.6B-Base/blob/da87bfb608c14b7cf20ba1ce41287e8de496c0cd/config.json>

## Yukabox audit

Read-only inspection on 2026-08-21:

| Resource | Observed |
| --- | --- |
| CPU | AMD Ryzen AI 9 HX 470 · 12 cores / 24 threads |
| RAM | 59 GiB total · about 50 GiB available during audit |
| swap | 8 GiB total |
| disk | about 1.7 TiB free in the workspace filesystem |
| graphics | integrated AMD Radeon 890M render device present |
| Python | 3.14.4 |
| ML runtime | PyTorch, Transformers, PEFT, Accelerate and ROCm not installed |

Conclusion: memory and disk are sufficient for a 0.6B development study. GPU
training is **not** assumed. The first approved setup must install a pinned
environment and measure one inference/gradient smoke before stating a run-time
estimate. Until that benchmark exists, “fits in memory” must not be presented
as “will train quickly.”

Proposed safety budget after approval:

- download cap: 2 GiB for model/tokenizer/config files;
- environment setup cap: 4 GiB;
- first execution cap: one compatibility and DoRA smoke, at most 2 hours;
- stop on out-of-memory, non-finite loss, unexpected parameter mutation, or
  inability to restore the untouched base hash.

The two-hour smoke is not a locked result. It exists to replace guesses about
speed with measurements before a longer run.

## Illustrative task world

The visible sample world has three fictional procedures:

```text
Kite(x, y)       -> one value from 00..1F
Tide(x, y, z)    -> one value from 00..1F
Ember(x, y)      -> one value from 00..1F
```

Each pocket sees worked examples from only one procedure. A combined prompt
provides all inputs and asks for the three results in an order expressed in
ordinary language. The complete answer looks like:

```text
T-0C / E-11 / K-07
```

There are `32³ = 32,768` possible complete answers. Blind whole-answer chance is
`1/32,768 ≈ 0.00305%`, not 50%. Even a perfect pair still has only `1/32`
chance of guessing the missing pocket's segment.

The rules and examples in `sample-tasks.json` are illustrative and public. They
test whether a human understands the benchmark. Locked coefficients, keys, and
combinations will be generated only after approval and isolated from merger
training.

Three example prompts and derivations are included in the public draft. The
generator produces twelve and tests every answer mechanically.

## Candidate architecture and DoRA recipe

Development paths:

| Pocket | Path | Initial DoRA recipe |
| --- | --- | --- |
| `E004-I1` | 6 compatible blocks | rank 8 |
| `E004-I2` | 12 compatible blocks | rank 8 |
| `E004-I3` | 24 compatible blocks | rank 8 |

Candidate DoRA target modules in each personal block:

```text
self_attn: q_proj, k_proj, v_proj, o_proj
mlp:       gate_proj, up_proj, down_proj
```

Only DoRA magnitude `m` and low-rank direction matrices `A/B` may train. Shared
stem/final path, matching base references, neural ABI projections, and other
pockets remain frozen. The same rank and target classes keep the first depth
comparison understandable. Exact trainable parameter counts will be verified
from the pinned implementation before the first optimizer step.

Distilling compatible 6/12 paths from the 24-block path is compatibility
training, not personal learning. It starts only after this checkpoint is
approved.

## Minimal comparisons

The eventual locked table contains:

1. base only;
2. each trained pocket alone;
3. every pair;
4. all three pockets;
5. all three without `z0`;
6. one wrong or missing pocket;
7. exact relevant-data RAG.

## Draft pass conditions

Numerical tolerances will be measured during the approved smoke and frozen
before the locked run. The non-negotiable logical conditions are already fixed:

- fresh personal deltas are numerically near zero;
- only declared DoRA parameters change;
- every pocket improves on its own held-out procedure;
- the full swarm beats base, every single, and every pair;
- removing any required pocket causes a measurable loss;
- removing `z0` hurts prompts that require shared language interpretation;
- partial, non-finite, or over-budget deltas contribute nothing;
- exact RAG remains visible and may honestly win.

## Decision requested

Approve only these actions:

1. create a pinned isolated ML environment;
2. download the stated Qwen revision within the caps above;
3. generate locked task splits;
4. run compatibility and DoRA **development smokes only**;
5. stop at Checkpoint 2 before merger evaluation.

No locked evaluation and no physical-device training are authorized by this
checkpoint.

# E001 — Personal Delta Towers

Status: **locked three-seed mechanism pilot completed; advance to E002**

Source: **D02 · H027**

> Can independently personalized `pocket i` compose a correct answer that the
> shared base and any one pocket i cannot produce alone?

E001 is the smallest neural test of the proposed Personal Delta Tower
architecture. It follows the public result contract in
[`METHOD.md`](../../METHOD.md). The locked pilot supports the narrow claim that
independently trained, ABI-compatible neural deltas can be composed. It does
not establish that a network of language models outperforms a frontier model.

## Definitions

- A **logical pocket i** has its own weights, training history, and capability.
- Two pocket i in the same specialty are different intelligences, not replicas.
- **Top-2 semantic redundancy** routes the same role to two distinct pocket i.
- An expert contribution is transactional: only a complete result can enter
  the merger. A partial delta is discarded in full.

If the preferred expert fails after it has already influenced autoregressive
tokens, a strict implementation must replay the answer without that expert.
The E001 pilot buffers expert capsules before merging, so incomplete work can
be removed without hidden residual influence.

## Architecture under test

```text
question refs -> shared stem -> trusted 24-layer base -> normalized z0
             |                    oracle route: two specialties
             |
             +-> top-2 pocket i for specialty A -> first complete delta A
             +-> top-2 pocket i for specialty B -> first complete delta B
                                                            |
                   FinalLayers(z0 + Clip(Merge(delta A, delta B)))
                                                            |
                                                         answer
```

For pocket i `j`:

```text
raw_delta_j = PersonalTower_j(h) - BaseTower_depth(j)(h)
delta_j     = ABIProjection_j(raw_delta_j)
```

The personal and base towers start identical, so a fresh pocket i returns zero
delta. The base reference and ABI shape stay fixed while the personal blocks
learn a local specialty.

## Private World pilot

Each locked world has four specialties, 64 private facts per specialty, and two
independently trained pocket i per specialty. Every specialty owns a private
key-to-bit mapping. A question requests two facts from two different
specialties. The four answer classes are the ordered pair of hidden bits:

```text
answer = 2 * bit_from_first_specialty + bit_from_second_specialty
```

No single pocket i has both required facts. Keys are split 44/9/11 within each
specialty before central training. The merger sees no test key until every
pocket i and central head is frozen. Pocket i do see their own complete private
fact table: the held-out boundary tests composition, not whether a pocket i can
infer a random unseen fact.

## Pre-registered comparisons

1. Shared base without personalized experts.
2. Depth/interface-matched fresh base clones whose canonical delta is zero.
3. Best single pocket i with the other required role withheld.
4. Oracle memory/RAG with both exact facts.
5. Personal Delta Towers with oracle routing.
6. Personal Delta Towers when the preferred candidate fails and the second
   distinct expert must complete the role.

## Primary metrics

- accuracy;
- lift over the strongest separately trained base, fresh-clone, or single-role
  control;
- strict joint-ablation success as a diagnostic, not a pass/fail target;
- causal loss when a required specialty is removed;
- backup recovery when the preferred expert is incomplete;
- zero-delta norm for a fresh pocket i.

Latency, memory, and bytes are recorded but are not pass/fail criteria in E001.

## Pilot gate

The architecture advances to a larger language-model test only if:

- every fresh pocket i has zero delta within numerical tolerance;
- top-2 candidates always have distinct logical identities;
- no partial expert result reaches the merger;
- the backup path preserves useful quality when the preferred expert fails;
- Personal Delta Towers beat the strongest trained control by at least 10
  percentage points on every locked seed;
- removing a necessary specialty causes a measurable, pre-specified loss.

The thresholds were locked in `configs/locked-pilot.json` before seeds
`17082101`, `17082102`, and `17082103` were executed.

## Locked result

All three unseen worlds passed every gate. Across seeds:

| condition | mean accuracy | min | max |
| --- | ---: | ---: | ---: |
| Personal Delta Towers | 100.00% | 100.00% | 100.00% |
| forced preferred-expert failure | 100.00% | 100.00% | 100.00% |
| strongest trained control | 49.36% | 46.28% | 55.44% |
| collective lift | +50.64 pp | +44.56 pp | +53.72 pp |

The complete suite summary is
[`artifacts/20260820T074133Z-suite-3-seeds/suite-summary.json`](artifacts/20260820T074133Z-suite-3-seeds/suite-summary.json).
Each seed directory contains all 1,452 task records, routes, completion states,
control predictions, hashes, resource use, and gate outcomes.

Conclusion: E001 supports moving to a less scripted experiment. It proves
neither emergent latent alignment nor useful language reasoning: every pocket
i was explicitly taught a shared one-hot neural ABI, routing was given, and all
computation ran in one CPU process.

## Reproduction

Host CPU environment:

```sh
cd /home/yuka/projects/joinmultiplayer.ai
python3 -m venv .venv
.venv/bin/python -m pip install -r \
  experiments/E001-personal-delta-towers/requirements-cpu.txt
PYTHONPATH=experiments/E001-personal-delta-towers/src \
  .venv/bin/python -m unittest discover \
  -s experiments/E001-personal-delta-towers/tests -v
PYTHONPATH=experiments/E001-personal-delta-towers/src \
  .venv/bin/python -m e001.run \
  --config experiments/E001-personal-delta-towers/configs/locked-pilot.json \
  --all-seeds
```

Container reproduction:

```sh
cd experiments/E001-personal-delta-towers
docker build -t joinmultiplayer-e001 .
docker run --rm -v "$PWD:/work" joinmultiplayer-e001
```

Small JSON/JSONL results belong in `artifacts/`. Model checkpoints are local
build products and are ignored by Git.

## Environment for the first run

```text
host: yukabox
CPU: AMD Ryzen AI 9 HX 470, 12 cores / 24 threads
RAM: 64 GB physical, 59 GiB visible to Linux
accelerator: Radeon 890M; not used by the first CPU pilot
OS: Ubuntu 26.04
```

The next stage is the same interface on a small open 24-layer language model,
first on yukabox CPU and then on its accelerator once the ROCm path is audited.

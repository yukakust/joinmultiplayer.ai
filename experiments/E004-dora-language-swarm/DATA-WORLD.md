# E004 public data world

Status: `ILLUSTRATIVE · NOT LOCKED · NOT A RESULT`

This public world lets a person inspect the future experiment before any model
is trained. It uses a separate public seed and cannot become locked evaluation
data.

## Eight visible demo pocket i

| i | Name | Personal rule | Visible update | Visible deletion |
| --- | --- | --- | --- | --- |
| P01 | Kite | `(617 × value + 710) mod 997` | `kite-01` | `kite-02` |
| P02 | Tide | `(535 × value + 338) mod 997` | `tide-01` | `tide-02` |
| P03 | Ember | `(853 × value + 894) mod 997` | `ember-01` | `ember-02` |
| P04 | Moss | `(592 × value + 821) mod 997` | `moss-01` | `moss-02` |
| P05 | Orbit | `(709 × value + 457) mod 997` | `orbit-01` | `orbit-02` |
| P06 | Lumen | `(978 × value + 288) mod 997` | `lumen-01` | `lumen-02` |
| P07 | Coral | `(231 × value + 149) mod 997` | `coral-01` | `coral-02` |
| P08 | Flint | `(480 × value + 157) mod 997` | `flint-01` | `flint-02` |

Each checked-in demo book exposes eight records so the arithmetic is readable.
The locked-book contract reserves 256 exact facts, 256 procedure examples, and
64 updates/deletions per pocket.

## What a task does

1. A question names one, two, or three required pocket i and one record from
   each.
2. Each pocket reads the latest local record state.
3. It applies its own rule and returns one value from `000..996`.
4. The source keeps all segments and calculates one positional seal.
5. A deleted record must return `ABSTAIN`, not its old value.

Example:

```text
PUBLIC-06 needs P01 + P04 + P08
P01 returns 431
P04 returns 801
P08 returns 121
source seal = (2×431 + 3×801 + 4×121) mod 997 = 758
answer = P01:431 | P04:801 | P08:121 | SEAL:758
```

A three-pocket answer has `997³ = 991,026,973` possible segment combinations.
A perfect pair still has only a `1/997` chance of guessing the missing segment.

## Population separation

- `P01..P08` are public demonstrations only.
- `S01..S16` will train central routers and mergers after approval.
- `I01..I08` will be generated separately for locked evaluation.
- `I09` appears only after the central system is frozen.

No locked salt, final book, evaluation label, retrieval index, or personal
weight exists yet. The future locked generator uses the public algorithm with a
separately created salt; only its commitment hash is published before the run.

## Files

- [`sample-tasks.json`](sample-tasks.json) — complete public books, tasks, and
  derivations;
- [`src/task_world.py`](src/task_world.py) — deterministic generator;
- [`tests/test_task_world.py`](tests/test_task_world.py) — integrity and leakage
  boundary checks.

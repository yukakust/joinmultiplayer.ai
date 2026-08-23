# E004 — the smallest useful DoRA language-swarm test

Status: `CHECKPOINT 1 PREPARING · NO TRAINING`

E004 asks whether three language pocket i can learn different small procedures
in local DoRA weights and solve unseen combined tasks that the base model, every
single pocket, and every pair cannot solve.

The minimal approved design lives in
[`../E003-first-physical-swarm/DORA-LANGUAGE-SWARM-PLAN.md`](../E003-first-physical-swarm/DORA-LANGUAGE-SWARM-PLAN.md).

Current public page: <https://joinmultiplayer.ai/experiment/?id=E004>

Current work is limited to preparing Checkpoint 1:

- read-only yukabox audit;
- one recommended pinned base model;
- illustrative, non-locked tasks and chance calculation;
- a candidate DoRA recipe and run boundary.

No model weights have been downloaded. No dependency has been installed. No
compatibility distillation, DoRA update, merger training, or evaluation has
started.

Standing rule: every meaningful step must leave owner-visible evidence. Prefer
an inspectable snapshot on the public E004 page; otherwise show it in Codex
first and publish the reviewed version next. Every snapshot states what
changed, shows the evidence, records the metric or failure, and names the next
step. No checkpoint advances without owner review.

Files:

- [`CHECKPOINT-1-DRAFT.md`](CHECKPOINT-1-DRAFT.md) — owner-facing decision;
- [`checkpoint-1.json`](checkpoint-1.json) — public-safe machine-readable draft;
- [`sample-tasks.json`](sample-tasks.json) — deterministic illustrative tasks;
- [`src/task_world.py`](src/task_world.py) — stdlib-only sample generator;
- [`tests/test_task_world.py`](tests/test_task_world.py) — chance and integrity checks.

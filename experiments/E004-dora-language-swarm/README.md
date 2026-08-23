# E004 — Architecture Arena

Status: `CHECKPOINT 1 REBUILDING · NO TRAINING`

E004 asks whether accessible knowledge and solution quality grow as `1, 2, 4,
8` independent pocket i join one temporary distributed neural network, and
whether a new ninth pocket can join after the central system is frozen.

Current public page: <https://joinmultiplayer.ai/experiment/?id=E004>

The approved planning direction compares five single-pass swarm interfaces:

1. RAG evidence;
2. learned memory tokens;
3. bounded latent deltas;
4. personal token-MoE experts;
5. temporary DoRA adapter assembly.

It also compares how one pocket stores unique knowledge: RAG, DoRA,
partial/full fine-tuning, trainable neural memory, and a hybrid. Recurrent
multi-round agent debate is excluded.

The synthetic population contains 16 surrogate pockets for central training,
8 unseen final pockets for locked evaluation, and a ninth plug-in pocket added
after the central system is frozen. Private final books never enter central
training.

The canonical protocol lives in
[`../E003-first-physical-swarm/DORA-LANGUAGE-SWARM-PLAN.md`](../E003-first-physical-swarm/DORA-LANGUAGE-SWARM-PLAN.md).

## Standing owner-visible evidence rule

Every meaningful step leaves evidence the owner can inspect. Prefer a reviewed
snapshot on the public E004 page; otherwise show it in Codex first and publish
the safe version next. Each stage states what changed, shows evidence, records
the metric or failure, and names the next step. No checkpoint advances without
owner review.

## Current boundary

No model weight or ML dependency has been downloaded for E004. No optimizer
step, RAG index, neural memory, router, merger, adapter, MoE expert, or locked
evaluation exists yet. Checkpoint 1 is a design artifact, not a result.

Current files:

- [`CHECKPOINT-1-DRAFT.md`](CHECKPOINT-1-DRAFT.md) — owner-facing arena decision;
- [`DATA-WORLD.md`](DATA-WORLD.md) — human-readable public data contract;
- [`sample-tasks.json`](sample-tasks.json) — eight public demo books and twelve
  mechanically derived tasks;
- [`src/task_world.py`](src/task_world.py) — deterministic public generator;
- [`tests/test_task_world.py`](tests/test_task_world.py) — integrity tests.

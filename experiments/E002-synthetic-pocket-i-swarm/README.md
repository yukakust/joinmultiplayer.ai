# E002 — synthetic pocket i swarm

The protocol remains an explicitly unlocked draft in
[`PROTOCOL.md`](PROTOCOL.md). R0001 is a reproducible development run, not an
accepted E002 result.

Run the tests and development experiment from the repository root:

```sh
PYTHONPATH=experiments/E002-synthetic-pocket-i-swarm/src \
  .venv/bin/python -m unittest discover \
  -s experiments/E002-synthetic-pocket-i-swarm/tests -v
PYTHONPATH=experiments/E002-synthetic-pocket-i-swarm/src \
  .venv/bin/python -m e002.run \
  --config experiments/E002-synthetic-pocket-i-swarm/configs/draft-r0001.json
```

Every run gets a new directory under `artifacts/` containing `summary.json`,
complete task-level `tasks.jsonl`, and a standalone interactive
`microscope.html`. Existing runs are never overwritten.

The current draft reports two axes separately: composition depth (every task
uses all N pockets) and quality on one fixed 32-pocket workload as more owners
become available. Do not collapse them into one ambiguous "swarm grows" chart.

The first accepted result must remain distinct from:

- a public design/build journal;
- a machine-completed run;
- a human inspection;
- an independent replication (`V`).

Only the last of these may place an independent dot on the experiment.

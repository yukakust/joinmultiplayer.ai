# Pocket i desktop

This directory turns the accepted E007 research modules into one portable,
inspectable desktop core. It is intentionally standard-library Python at the
first checkpoint so the orchestration contract is identical on macOS, Windows
and Linux.

Checkpoint 1 contains the core and tests, not a finished application. Model
runtimes, real local-library adapters, network transport, UI and installers are
connected in later checkpoints from
[`DESKTOP_MVP_PLAN.md`](../experiments/E007-harness-mvp/DESKTOP_MVP_PLAN.md).

Run the core tests:

```bash
PYTHONPATH=desktop python3 -m unittest discover -s desktop/tests -v
```

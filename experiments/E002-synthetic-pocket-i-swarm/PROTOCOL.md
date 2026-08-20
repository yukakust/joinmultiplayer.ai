# E002 — synthetic pocket i swarm

Status: **DRAFT — not locked, not run**  
Main hypothesis: `H0001`  
Protocol version: `E002-draft-v0.1`

## Question

Can independently trained personal neural branches combine non-overlapping
private knowledge through a shared neural interface, and does useful coverage
grow as the number of branches grows?

This is a synthetic mechanism experiment. A positive result would justify
building the first real pocket i alpha. It would not prove that a global swarm
beats a frontier model.

## Visible first case

Begin with two synthetic pocket i under a human-readable microscope.

- Both start from the same frozen base/interface.
- Each receives a different private training set.
- Each must change its own weights through an ordinary local loss.
- Neither private set is available to the source merger or shared tail.
- The task requires both private values plus a public operation represented by
  the common path `z0`.
- The answer space contains 256 classes, so blind guessing succeeds with
  probability `1/256` per task.

The interactive record must show the private examples, loss curve, which
weights changed, the returned bounded delta, merge, final class distribution,
and every ablation outcome. It must never claim that a model learned more than
the recorded weights and held-out tasks demonstrate.

## Scale axis

After the two-i case is inspectable, run the same protocol for:

```text
N = 2, 4, 8, 16, 32
```

The primary chart is not an equal-compute leaderboard. It is the swarm scaling
curve:

```text
number of independent i
→ unique learned private coverage
→ compositional task difficulty
→ held-out swarm quality
```

Report total compute, bytes, latency, active branches, and failures so the cost
of coordination remains visible. Equal-budget controls diagnose efficiency;
the main hypothesis asks whether additional independent experience and compute
continue to add useful capability.

## Required controls

The locked protocol must include at least:

1. shared base only;
2. repeated fresh copies of the shared base;
3. each required personal i alone;
4. all personal deltas with `z0` removed;
5. shuffled or wrong personal deltas;
6. exact relevant-data RAG;
7. a text-agent/ensemble synthesis baseline;
8. preferred specialist interrupted, complete backup used;
9. incomplete payload presented to the transaction boundary;
10. one malicious but norm-bounded delta.

## Falsification gates before lock

The experiment fails to support the mechanism if any of the following is true:

- the source or merger can recover locked test values without the personal
  branches;
- the personal weights do not measurably change;
- a single branch or the no-`z0` path solves tasks that were declared
  compositional;
- performance does not rise when genuinely useful non-overlapping branches are
  added;
- exact RAG explains all gains with lower coordination cost and the neural path
  adds no measurable procedural or representational capability;
- a missing or incomplete branch can silently contribute partial state;
- the result cannot be reproduced from a versioned config and artifact
  manifest.

Thresholds, seeds, data generation, train/test isolation, hardware reporting,
and the exact definition of "useful coverage" remain open. A human must review
and explicitly lock them before the first result-bearing run.

## Public run journal

Design and implementation runs may be streamed to joinmultiplayer.ai through
the Codex Lab Connector. Public events contain filtered messages, plan text,
action status, relative changed-file names, and metrics. They exclude raw
reasoning, command output, file contents, environment variables, credentials,
and local absolute paths.


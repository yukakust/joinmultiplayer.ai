# E002 development journal

## R0001 — preserved failed rehearsal

Status: **development failure; protocol remained DRAFT**

The first full execution of draft v0.2 is retained in `artifacts/R0001`.
Full-swarm accuracy was 100% for N=2,4,8,16,32, but the aggregate draft gate
failed. Two causes were found:

- 32 tasks made a 2% ceiling for a 1/256 chance control unstable; one correct
  guess produces 3.125%.
- swapping two additive contributions is not a valid universal negative
  control. At N=2, equal public signs make the swap exactly invariant, and the
  observed shuffled accuracy was 62.5%.

No file in that run directory was overwritten. Draft v0.3 repairs the test
design with 256 tasks, a 5% chance-control ceiling, and wrong-key contributions
from every pocket. Any revised execution uses a new directory and remains
development-only.

## R0001-v0.3-revision — passing development rehearsal

Status: **all draft gates passed; protocol still DRAFT**

Across 256 tasks at every N, full-swarm and interrupted-backup accuracy were
100%. Unique private coverage rose 16, 32, 64, 128, 256 values. Aggregate
accuracy after removing every pocket in turn was 0.214%. Exact RAG and the
symbolic text-ensemble ceiling were also 100%; the neural path showed no
advantage over either. This revision predated the artifact manifest and remains
untouched. A further manifest-bearing run is required for the reproducibility
gate.

## R0001-v0.3-manifest — final development artifact

Status: **all v0.3 draft gates passed; superseded by human review**

This run reproduced the v0.3 revision task-for-task and adds `manifest.json`
with byte counts and SHA-256 hashes for the summary, complete task stream, and
interactive microscope. It is the preferred R0001 development artifact. It is
not an accepted E002 result and does not support changing H0001's status.

Human review found that v0.3's `N` runs changed the workload at every scale and
were already 100% accurate at N=2. They demonstrated composition depth, not
quality growth on one fixed workload. The label `unique private values` also
counted key→value associations, not mathematically unique byte values, and the
weight-change gate inspected only the visible two-pocket case. Draft v0.4
corrects all three issues and retains this artifact unchanged.

## R0001-v0.4-fixed-workload — passing development rehearsal

Status: **all v0.4 draft gates passed; protocol still DRAFT; awaiting human inspection**

The v0.4 runner adds a fixed 32-pocket workload with evenly covered ordered
expert pairs. It evaluates that exact workload while 2, 4, 8, 16, and 32 owners
are available, alongside the original all-N composition-depth curve. A final
development artifact must point to the committed source revision that produced
it and include a verified content manifest.

The run points to source revision `d68b9031947f19170fe9e4c6068d9e1bf159a9f3`
and its manifest verifies. On the fixed 1,984-task workload, accuracy rose:

```text
available pocket i:   2      4      8      16      32
accuracy:            0.7%   1.7%   6.1%   24.5%   100.0%
```

The oracle-answerable fractions are approximately 0.2%, 1.2%, 5.6%, 24.2%,
and 100%; the small excess is chance prediction on tasks whose required owner
is unavailable. This curve therefore demonstrates coverage under oracle
routing, not learned discovery or superiority over exact retrieval. The
separate composition-depth curve remains 100% at every N and shows only that
the synthetic merge continues to work as fan-in increases.

# E004 four-interface arena protocol v0.1

Status: `PRE-REGISTERED DEVELOPMENT PROTOCOL · NO ARENA RESULT YET`

## Claim under test

Can independently learned pocket i expose more usable knowledge as more owners
join a single-pass swarm, without copying all private books into one central
model?

This run compares four **swarm interfaces**. It does not compare four copies of
the same weights. Every interface receives the same base lineage, books, task
splits, required-pocket oracle, answer contract, and metrics. Each interface is
allowed to learn the parameters its own mechanism requires.

## Two stages, never mixed

1. **Public development arena.** Eight readable `P01..P08` books and twelve
   tasks catch implementation failures. Every output, including failures, is
   published. These scores support no scientific claim.
2. **Locked arena.** Only after all four interfaces execute end to end, new
   surrogate and final books are generated from a committed salt. Central
   components train on `S01..S16`; `I01..I08` remain unseen until one frozen
   evaluation; `I09` joins after the center is frozen.

The present authorization starts stage 1. A locked run must use the thresholds
already published at Checkpoint 1 and may not tune them after seeing results.

## Immutable public development input

- frozen base: `Qwen/Qwen3-0.6B-Base` revision
  `da87bfb608c14b7cf20ba1ce41287e8de496c0cd`;
- books/tasks SHA-256:
  `f3fd2cb5730ab602ef232ddf6dfa8b8f0376561234ab050a42543fd94a685370`;
- generator SHA-256:
  `59431ca9c98ed327d0c4ade06db2d2ebc82db09829dcf01642303cce3496eb70`;
- eight books, twelve tasks: two single, three pair, four triple, one updated,
  and two deletion tasks;
- every answer is an exact structured string, never a binary label;
- selected pockets are supplied by an oracle in the component tournament.

## Four interfaces

### A1 · RAG evidence swarm

Each selected pocket reads its own current record and returns one typed,
owner-approved evidence capsule. The source assembles the segments and seal.
Raw books never leave the pocket. This is the factual upper control and uses no
gradient training.

### A2 · Neural-memory swarm

Each pocket learns a bounded bank of local key/value memory tokens from the
same book. For a query it returns a fixed-size capsule; a common source merger
reads all completed capsules once. No repeated conversation is allowed.

### A3 · Latent-delta swarm

Each pocket learns local personal weights against the shared frozen base. It
returns a normalized, norm-bounded residual—what it adds beyond the common
representation. A common source merger applies the completed deltas once.

### A4 · Personal token-MoE

Each pocket owns a personal FFN expert. For every generated answer token, the
source sends the same canonical hidden state to all selected experts in
parallel and fuses the returned bounded residuals. Autoregressive tokens remain
sequential; there are no whole-answer debate rounds.

## Atomic completion rule

Partial contributions are never fused. If one selected pocket fails, its
entire contribution is absent. The task must either abstain or be marked
incomplete; it may not silently use half a capsule. Development runs simulate
parallel branches on one host but record this honestly.

## Metrics reported for every architecture

- exact complete-answer accuracy;
- exact per-pocket segment accuracy;
- single, pair, triple, update, and deletion accuracy separately;
- `N=1,2,4,8` accessible-knowledge coverage;
- required-pocket removal and correct abstention;
- irrelevant and duplicate-pocket sensitivity;
- trainable parameters, artifact bytes, elapsed time, peak RAM, and estimated
  network bytes;
- every failed task with expected and actual output.

Compute, bytes, and latency are reported controls, not equalized pass
conditions. The swarm is meant to gain total data and compute as owners join.

## Controls

- frozen base alone;
- best single and relevant pair;
- exact relevant-data RAG;
- text/logit assembly where meaningful;
- missing, duplicate, irrelevant, stale, malformed, and late contributions.

The first component run uses oracle routing. Learned routing is a separate
experiment so a routing error cannot masquerade as an interface failure.

## Development stop rules

An interface is published as `failed` if it crashes, leaks another pocket's
book, consumes partial output, produces non-finite values, or cannot beat its
own frozen/untrained state after two documented protocol-preserving attempts.
Changing data, split, answer, or threshold creates a new protocol version; it
may not overwrite this one.

Passing development means only that the implementation executes and its
measurement is trustworthy. It does not support the swarm hypothesis.

## Execution boundary

Heavy jobs run on yukabox only from `08:00–23:45 Europe/Berlin`, checkpoint by
`23:45`, stop by `23:55`, using at most 22 CPU threads and 52 GiB RAM. Every
architecture receives its own immutable public result artifact as soon as it
finishes or fails.

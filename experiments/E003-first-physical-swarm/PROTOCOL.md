# E003 protocol v0.1 — three physical devices

## Question

Can three physical devices, each with distinct locally updated weights, accept
one coordinated workload and return complete neural capsules that compose into
a correct answer which no single device contains?

## Fixed design

- Three roles and exactly three physical devices.
- Sixteen private key/value examples per role; values are in `[0, 15]`.
- The server deterministically assigns different controlled shards over each
  node's private HTTPS token. The shards are private from other participants,
  but not from the experiment server; this is not a privacy claim.
- Every device starts with the same all-zero 16×16 weight matrix and performs
  180 epochs of local cross-entropy gradient descent.
- The server sees the checksum, local accuracy, and delta norm, but not the
  trained weight matrix.
- After all nodes are ready, the owner starts 64 fixed tasks. Each device sees
  only its role's key and returns one complete batch of 16-logit capsules.
- The server accepts no partial batch. It merges the argmax digit from each
  role into one of `16³ = 4,096` whole answers.

## Required observations

1. Three distinct node identities and device labels are present.
2. Each node reports non-zero delta norm and 100% local training accuracy.
3. All three complete capsule batches arrive.
4. Whole-answer accuracy and per-node digit accuracy are reported.
5. Removing each node and replacing its digit with the unchanged base output
   is reported separately.
6. Only aggregate metrics are public after explicit owner approval. Join and
   node tokens, controlled tables, weights, and capsules remain private.

## Interpretation boundary

Passing E003 shows that the physical task path works and that three locally
personalized toy neural modules can compose. It does not establish useful
language capability, safe latent fusion, owner privacy, Byzantine resistance,
swarm scaling, or superiority over RAG/symbolic composition. Those require
later experiments.

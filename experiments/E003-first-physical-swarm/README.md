# E003 — first physical pocket i swarm

Status: `DRAFT · ready for the first owner-run`

E003 moves the smallest synthetic composition mechanism onto three physical
devices. A phone, a Mac, and a server each receive one non-overlapping
controlled shard, begin from the same zero-weight 16×16 classifier, and update
their weights locally. The coordinator sends 64 tasks. Each whole answer is a
three-digit base-16 value, so there are 4,096 possible answers and a random
whole-answer guess succeeds with probability 1/4,096.

This is a control-plane and physical-composition test. It does not yet test a
language model, the proposed shared-stem/personal-delta/final-layer neural ABI,
per-token WAN inference, private human knowledge, or H0001 itself.

The human-readable client is `/network/`. Phone and Mac nodes run entirely in
the browser. A headless Python node is available at `/network/pocket_node.py`.

See [PROTOCOL.md](PROTOCOL.md) for the preregistered flow and boundaries.

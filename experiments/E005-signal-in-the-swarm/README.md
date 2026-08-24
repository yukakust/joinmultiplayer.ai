# E005 — Signal in the Swarm

E005 follows E004 without replacing or deleting it. E004 tested four transport
and composition interfaces on public synthetic records. E005 tests the missing
selection problem: whether a growing swarm can find a complementary combination
of understanding and evidence while preserving a credible minority and
discounting dependent copies.

The experiment begins with a public natural-language development world. No
weight training may begin until the owner has inspected that world on
joinmultiplayer.ai.

Current status: **Gate 3 development controls completed and manually reviewed;
owner visual checkpoint active before any personal-weight training**.

Gate 3 compared exact-word retrieval, frozen-Qwen semantic retrieval, raw
majority, the deterministic evidence graph, and an oracle source set across six
questions in English and Russian. The evidence graph and oracle recovered the
ideal records in 12/12 generations, but the frozen Qwen generator produced only
6/12 correct generations. In the two clearest failures it reversed an explicit
"keep closed" instruction and recommended an intervention despite an explicit
requirement to wait for more evidence. This is a public synthetic development
result, not evidence of learned routing or generalization. The complete artifact
is `site/experiments/E005/gate-3-public-v0.1.json`.

The primary browser review at `/experiment/e005/gate-3/` groups results by
question in a 6×5 matrix and keeps source selection separate from answer
correctness. Owner confirmations and corrections are browser-local until the
owner explicitly asks Morrow to publish the checkpoint. The previous exhaustive
method-first rendering remains available at `/experiment/e005/gate-3/raw/`.
The matrix uses one conservative bilingual rating per task and method: green
requires both RU and EN generations to be correct, red means at least one is
wrong or contradictory, and yellow covers the remaining incomplete cases. The
site-wide EN/RU control changes the complete interface and the visible raw
generation; it never changes that paired rating. All five Gate 3 columns use the
same frozen Qwen3-0.6B Base with no DoRA and no fine-tuning; only evidence
selection differs.

See [PROTOCOL.md](PROTOCOL.md).

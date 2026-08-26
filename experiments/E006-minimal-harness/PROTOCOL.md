# E006 — minimal harness

E006 reuses the fictional Luma world and freezes ten English questions before
the first answer. Every question has three oracle-selected pocket i: one owns a
diagnostic record, one owns a conditional action record, and one owns a similar
but irrelevant record. No single local record contains the complete answer.

The first stage does not test search or routing. It compares only how the same
already-selected knowledge reaches the final frozen Qwen:

1. `centralized_context`: all three raw records are placed in one prompt;
2. `free_text_swarm`: each pocket sends an unrestricted note;
3. `minimal_harness`: each pocket must send `status`, `claim`, `source`, `quote`,
   and `missing`; unsupported capsules are rejected before assembly.

All conditions use the same Qwen3-0.6B-Instruct-2507 checkpoint and greedy
decoding. No weights train. Raw local messages, rejected capsules, final
answers, and failed attempts remain part of the result.

The exact frozen public contract is
`/experiments/E006/protocol-v0.2.json`; v0.1 was superseded before inference
because it incorrectly called the oracle-selected central context a RAG search.

This is a ten-question synthetic development experiment. Automatic phrase
checks are alarms only. All thirty final answers require blind semantic review,
followed by owner review before an architecture claim.

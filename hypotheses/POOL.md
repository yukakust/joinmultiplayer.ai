# Hypothesis Pool v0.1

> Nothing here is true yet.

`ı` untested · `→` in experiment · `i` tested

## Composition

- `H001` `ı` A team of small models can beat one large model on decomposable tasks under the same total inference budget.
- `H002` `ı` A heterogeneous team can outperform a same-size team of identical models.
- `H003` `ı` Small specialists can outperform an equally priced generalist when the task crosses several domains.
- `H004` `ı` Assigning roles dynamically can outperform giving every intelligence a fixed role.
- `H005` `ı` Giving tools to small intelligences can close more of the performance gap than adding parameters to one model.
- `H027` `→` ABI-compatible personal delta towers can compose information that the shared base, fresh clones, or either single tower lacks. E001 passed; independent replication is pending.

## Deliberation

- `H006` `ı` Independent answers followed by a vote can be more reliable than one answer of equal cost.
- `H007` `ı` Critique and revision can outperform majority voting under the same budget.
- `H008` `ı` Structured dissent can find more errors than free-form discussion.
- `H009` `ı` Confidence-weighted aggregation can outperform majority voting when confidence is calibrated.
- `H010` `ı` Stopping when consensus stabilizes can preserve quality while using fewer tokens than fixed rounds.

## Memory

- `H011` `ı` Shared memory can prevent a group from repeating mistakes across tasks.
- `H012` `ı` Private memories with selective sharing can outperform one global memory.
- `H013` `ı` One intelligence can teach a useful strategy to another without changing either model's weights.
- `H014` `ı` Forgetting low-quality memories can prevent errors from spreading through the group.
- `H015` `ı` Attaching provenance to every shared claim can improve the accuracy of the final answer.

## Networks

- `H016` `ı` Sparse communication can match all-to-all discussion with fewer tokens.
- `H017` `ı` Decentralized coordination can keep working after a central context window becomes a bottleneck.
- `H018` `ı` Rotating the coordinator can outperform relying on one permanent leader.
- `H019` `ı` Local subteams that merge conclusions can outperform one flat discussion on complex tasks.
- `H020` `ı` A strict communication limit can force intelligences to exchange more useful representations.

## Boundaries

- `H021` `ı` Adding more intelligences can eventually reduce quality by amplifying correlated errors.
- `H022` `ı` Disagreement between intelligences can predict failure better than their average self-confidence.
- `H023` `ı` Diversity helps only while its information gain exceeds its coordination cost.
- `H024` `ı` One large model can remain better on tasks that resist decomposition.
- `H025` `ı` A group of small intelligences can degrade more gracefully than one large intelligence when part of the system fails.

## Questions

- `H026` `ı` Independent intelligences create more value by discovering missing questions than by pooling final answers.

## Selection pressure

The next experiment should be:

- close to the main question;
- falsifiable;
- fair about total cost;
- small enough to reproduce.

When a hypothesis is selected, give it its own file and keep its `H` ID attached
through every experiment and result. Add the next seed as `H027`.

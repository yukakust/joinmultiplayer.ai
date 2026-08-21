# Pocket i swarm map — text companion

Board:
<https://miro.com/app/board/uXjVHwDwQAw=/>

Miro area title:

> POCKET I · ПЕРВЫЕ ТРИ И ИХ SWARM

This file is the durable text companion to the five new Miro frames. The Miro
objects were added as a separate cluster to the right of the existing Opla and
Wingle material. No existing board item was edited or deleted.

## One sentence

> Создать вместе → забрать с собой → вырастить по-своему → объединиться,
> оставаясь собой.

## 1. One pocket i and the swarm

One pocket i contains:

1. **A shared language brain.** It already knows how to read, write, and perform
   general reasoning.
2. **Owner-controlled memory.** Precise and changing facts can be inspected,
   corrected, exported, and deleted.
3. **Personal neural skills.** A bounded set of local weights learns stable
   procedures, preferences, and representations.
4. **An honest abstention.** The pocket i can report that it adds nothing useful
   to this question.
5. **One shared connector — the neural ABI.** Different pocket i return results
   in one compatible shape and scale.

The pocket i does not send its entire brain or private notebook. It returns a
bounded neural contribution called `delta`:

```text
delta_i = what PersonalTower_i adds beyond its matching BaseTower
```

A fresh pocket i begins as a copy of its matching base, so its delta should be
approximately zero. As it learns, its delta starts representing what this
particular i adds.

A swarm is several different pocket i contributing different deltas to one
temporary model. Their agreement is not treated as truth automatically, and
two devices owned by the same logical i do not count as two independent minds.

## 2. How pocket i connect

The child-level explanation is:

```text
question
  → shared beginning makes a half-thought h
  → selected pocket i think in parallel
  → each returns one complete bounded delta
  → the source validates and merges the deltas
  → shared final layers turn the result into the answer
```

The devices do not need to exchange personal diaries with one another. For a
neural query, the source sends a shared hidden representation `h`. Each selected
branch processes it with its own weights and allowed local memory.

An incomplete contribution crosses no transaction boundary. If a selected i
disconnects before its complete result arrives, its partial state is discarded.
Later, the router may send one specialty to two different pocket i and accept
the first complete valid contribution. They are two independent specialists,
not replicas of the same intelligence.

The intended inference equation is:

```text
z0 = TrustedCommonPath(h)

raw_delta_i = PersonalTower_i,d(h, allowed_local_memory)
              - BaseTower_d(h)

delta_i = BoundAndNormalize(FrozenProjection_d(raw_delta_i))

answer = FinalLayers(z0 + Merge(delta_1, delta_2, ..., metadata))
```

One request temporarily materializes one larger sparse neural network from a
shared beginning, a selected set of personal branches, and a shared end.

## 3. How we plan to build the first three

The layer counts are starting hypotheses, not promises:

| Device | First intended branch | Honest first limitation |
| --- | --- | --- |
| Phone | short branch, around 6 blocks | may begin with memory and a small adapter rather than training six full blocks |
| MacBook | medium branch, around 12 blocks | likely source device and local answer merger |
| yukabox | deep branch, around 24 blocks | prepares models and performs the heaviest training |

Build order:

1. Select a small open pretrained language model for shared language ability.
2. On yukabox, derive and train compatible 6-, 12-, and 24-block paths that
   speak through one versioned neural ABI.
3. Run all three as isolated processes on yukabox first. At this point they are
   simulated owners, not three physical pocket i.
4. Make one complete task inspectable: training data, changed weights, delta,
   merge, output, and every ablation.
5. Move inference-only branches to the phone, Mac, and yukabox.
6. Enable local training on each physical device only after checkpoint,
   deletion, evaluation, and rollback work there.

If a device cannot support the planned depth, reduce the depth or start with an
adapter. Never label a browser adapter update as full transformer training.

## 4. How each pocket i learns

The owner explicitly chooses a lesson. Nothing silently scans the filesystem,
messages, accounts, or browser history.

Three kinds of learning remain separate:

### Mutable fact

Store it in local inspectable memory/RAG when it must be exact, attributable,
correctable, or deletable.

### Stable capability

Train personal weights when the lesson is a stable skill, procedure, preference,
or representation that cannot be reduced to retrieving one document.

### Shared language competence

Keep the common pretrained model frozen during the first experiment. Updating
the shared base is a later experiment with its own consent and regression suite.

Every local training cycle is:

```text
owner selects examples
  → keep a local held-out exam
  → evaluate before training
  → update only declared personal parameters
  → evaluate after training
  → promote the checkpoint if it improved
  → otherwise roll back
```

The owner must be able to see what data was used, what parameter groups changed,
what the local and global regressions show, and how to remove the update.

## 5. The first honest test

The phone learns private component `A`, the Mac learns `B`, and yukabox learns
`C`. The final task requires `A + B + C` and a public language operation supplied
by the common path `z0`.

The answer space must be large enough that random whole-answer guessing is
negligible. The source and merger must not see locked private answers during
training.

Compare:

1. shared base only;
2. fresh unpersonalized depth-matched branches;
3. each personal branch alone;
4. every pair;
5. all three together;
6. all three without `z0`;
7. wrong or shuffled branches;
8. one missing branch and explicit abstention;
9. exact relevant-data RAG;
10. text-agent synthesis with the same information;
11. an incomplete contribution;
12. a bounded malformed or adversarial delta.

### Success means

- fresh branches return deltas near zero;
- local training changes only allowed personal parameters;
- the base, every single branch, and every pair fail the locked three-way task;
- all three solve new held-out combinations;
- removing any required i causes a measurable loss;
- removing `z0` hurts tasks designed to require common language competence;
- different depths obey the same frozen ABI;
- a human can inspect and reproduce the complete path.

### Failure is also a valid result

Stop and report failure or inconclusive evidence when:

- the common model or one i solves the supposedly compositional task;
- the source or merger leaked locked answers;
- 6-, 12-, and 24-block paths do not maintain one stable ABI;
- personalization destroys ordinary language behavior;
- test thresholds change after seeing locked results;
- exact RAG explains all useful behavior more simply and the neural path adds
  no measurable learned procedure;
- the experiment cannot show a person what actually learned.

## Immediate sequence

```text
prove the language mechanism on yukabox
  → inspect it with a microscope
  → move it to phone + Mac + server
  → train locally under owner control
  → test the first physical swarm
  → only then scale the swarm
```

The detailed implementation handoff is
[`NEXT-LANGUAGE-MODEL-HANDOFF.md`](NEXT-LANGUAGE-MODEL-HANDOFF.md). The research
boundary and reusable prior art are recorded in
[`PERSONAL-DELTA-LM-ARCHITECTURE.md`](PERSONAL-DELTA-LM-ARCHITECTURE.md).

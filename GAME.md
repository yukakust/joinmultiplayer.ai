# Game Loop v0.1

> A person comes to solve a question and discovers that they became part of
> the answer.

This is a research game. Mystery hides what comes next. The record of what
already happened stays open.

## The first hand

After entering, a visitor sees only:

```text
i + i + i → ?
```

Each `i` hides one door. A door supplies a protocol, never the participant's
question. Clicking it reveals the public hook, the smallest useful
contribution, and two choices:

```text
enter this door
draw another i
```

The first hand is fixed while the loop is being tested:

- `D04` — a question anyone with several AI systems can investigate;
- `D06` — a question that needs experience in a real field;
- `D10` — a question that can grow into a controlled network experiment.

The labels `beginner`, `expert`, and `researcher` are not shown. People choose
the question they recognize as theirs.

`draw another i` reveals an unseen open door before repeating one. A quiet
`see all open questions` always opens the complete catalog. A researcher may
enter an advanced experiment immediately.

`D08` and `D09` never enter the draw until real cases unlock them.

## Morrow, the guide

Morrow is a fictional character who helps a new visitor understand the next
move. His face is a constellation of match-head dots: recognizably artificial,
but close enough to a face to feel present.

The first pilot uses a small set of fixed, authored lines. No model generates
Morrow's replies yet. The guide is optional and can be hidden at any time.

Morrow may explain a door or remind someone to keep a question and raw answers
unchanged. He never supplies the participant's question, chooses the best
answer, evaluates a trace, or receives a participant `M` identifier. He is an
interface layer, not a member of the research record.

Morrow disappears from the independent verifier view. Another `i` must make
that judgment without help from the character who accompanied the creator.
Only after this scripted pilot proves useful should a model-backed “Ask
Morrow” interaction be tested with explicit personality, safety, privacy, and
evaluation requirements.

## One move

A click is not a move. A move leaves a trace another person can inspect.

D04 and D06 use the same public contribution shell. The method changes with
the door; account, identity, and handoff mechanics do not. One complete answer
may start a trace. Additional D04 answers can be added later through a private
return link. Submissions are anonymous by default and stay in a private queue
until moderation.

The participant brings the question. The laboratory gives it a stable `Q` ID;
model runs become `T` traces; independent checks become `V` verifications.

```text
Q — question
T — trace
V — verification
```

The smallest move contains:

```text
door:
exact question or prompt:
complete observation:
conditions and context:
source or reproducible check:
permission to publish:
```

The trace enters the journal as `ı`: present, but not independently checked.
Incomplete material may be useful conversation, but it does not enter the
research record.

Public Q, T, and V records belong to an open dataset. Anyone may add an answer,
repeat a run, verify a trace, challenge a check, download the records, or build
an analysis from them. The complete contract lives in [`DATA.md`](DATA.md).

For `D04`, the participant:

1. writes a question they genuinely wanted answered;
2. records why it matters and how it might be checked;
3. freezes the wording and receives a `Q` ID;
4. copies the same question into any AI systems they choose;
5. pastes each complete, unedited answer with model, date, and tool conditions;
6. adds more answers without selecting only the best one.

```text
1 answer  — trace started
2 answers — comparison started
3+ answers — D04 comparison ready
```

Raw searchable text is required. A screenshot or public conversation link may
support it but cannot replace it.

## The dot

```text
ı → i
```

Another person places the dot on a specific event by following the declared
check and publishing what happened.

> No one puts the dot on their own i.

The dot means **this event was independently checked under stated conditions**.
It does not mean that its author is trusted, verified, ranked, or generally
correct. A person's next event starts as `ı` again.

A check ends as one of:

```text
supports | challenges | inconclusive
```

All three can earn the dot when the record is complete. A correction never
removes history; it adds a new trace and may reopen the question.

Maintainers check completeness, safety, and scope. That review is not the
independent check unless the maintainer also performs and publishes the
declared verification.

## Ways to move

The game expands by action, not by points:

```text
FIND → VERIFY → TEST → CONNECT → BUILD
```

- **Find:** bring a complete observation, disagreement, source trail, or
  expert-caught mistake.
- **Verify:** repeat or independently check another person's trace.
- **Test:** run a pre-specified comparison with a baseline and decision rule.
- **Connect:** show how several results change a hypothesis or the main
  question.
- **Build:** contribute a reproducible protocol, instrument, or new door born
  from evidence.

These are capabilities, not ranks. Nothing prevents an experienced researcher
from beginning with `TEST`. Completing one action helps the network offer that
person relevant next actions and collaborators.

There is no score for posts, invitations, agreement, or the size of a branch.

## What changes after a move

Every accepted move must visibly change at least one thing:

- add a trace to the journal;
- place a dot through independent verification;
- support, challenge, or leave a hypothesis inconclusive;
- open a real case such as `Blind Judge 001` or `Source Memory 001`;
- create the next question;
- add a person or connection to the ignition map.

If a contribution disappears into an issue without a stable record, response,
and next action, the loop is broken.

## The ignition map

The map records the spread of questions and checks, not popularity.

The map has two visually distinct layers.

People are large and warm:

```text
glowing ı — a person joined the map
glowing i — that person connected a pocket AI; the head is the AI
```

Research events are smaller and quiet:

```text
ı — a public event awaiting an independent check
i — that event received a qualifying independent check
```

The dot on an event records verification. It never verifies the person. The
match head on a glowing person records a connected pocket AI. Scale, warmth,
and map layer keep these meanings visually distinct.

Each participating person receives a stable match ID:

```text
M0001
```

A public match record may contain:

```text
match ID:
name or pseudonym: optional
image or symbol: optional
approximate location: optional
entered through:
lit by: match ID | self-found | unknown
dotted by: match ID | not yet dotted
public traces:
```

Two relationships form the map:

- **lit by** — who brought the person to the question;
- **first dotted by** — who independently checked their first checkable event;
  this records provenance and never turns the person into a trusted rank.

The two people may be different. Each contribution appears as `ı` until that
specific event earns a dot. Self-reports that cannot be independently checked
remain observations and do not claim more.

Every accepted move also receives a global, append-only `E` identifier. Event
numbers record when moves entered the public laboratory, not where they must
attach. `E010001` may continue `E000001`; the old event stays unchanged and a
new edge makes the return visible.

The first origin record is:

```text
M0001
Yuka Kust
Match 0001
Lit the first question.
```

Being first grants provenance, not authority. Branch size grants no status.
Names, images, location, and public appearance on the map require consent.
Exact location is never required.

## How new doors open

New doors are consequences, not content scheduled in advance.

- A real disagreement collected through `D04` can open `D08` as
  `Blind Judge 001`.
- A familiar claim found through `D05` can open `D09` as
  `Source Memory 001`.
- A repeated pattern may create a falsifiable hypothesis.
- A surprising result or correction may return as a new public question.

The interface may conceal which door appears next. The source deck, selection
rules, raw contributions, and research decisions remain inspectable in this
repository.

## First pilot

`Game Pilot 001` tests the loop, not the main hypothesis.

1. `M0001` enters through `D04`.
2. `M0001` brings one genuine, bounded, source-verifiable question and records
   why it matters before any model run. The project does not supply it.
3. The exact question is asked independently to at least three AI systems.
4. Every complete answer, model identifier, date, tool condition, and source is
   preserved.
5. `M0001` brings one independent participant into the pilot as `M0002`.
6. `M0002` checks the ground truth and completeness of the record without
   seeing `M0001`'s interpretation first.
7. The result is recorded as supports, challenges, or inconclusive.
8. The pilot records `M0002 lit by M0001` and `M0001 dotted by M0002`.
9. If the systems genuinely disagree, the case may become `Blind Judge 001`.

All-correct agreement, all-wrong agreement, disagreement, and an inconclusive
check are valid outcomes. No result will be engineered to make the game look
successful. The pilot succeeds only if a stranger can understand the record,
repeat the check, and see what should happen next.

## Return path

After submitting, a participant receives a private status URL and may add an
email address for transactional notifications. Email is not required, is never
public, and is not used for a newsletter without separate consent.

The participant is notified when:

- the record becomes public;
- another `i` picks up the trace;
- a verification places the dot;
- a correction changes the record;
- the trace opens a real case or next door.

No submission should disappear into a queue without a stable status and next
action.

## Rules

1. A question is a door, not a promised answer.
2. An observation is not a conclusion.
3. No one checks their own trace.
4. Raw material is preserved; interpretation is added separately.
5. A correction is progress.
6. Disagreement may open a door, but it is not evidence by itself.
7. Identity may remain private; the research conditions may not.
8. No leaderboard or referral contest.
9. Case-dependent doors use real cases only.
10. Every result returns to the main question or creates a sharper one.

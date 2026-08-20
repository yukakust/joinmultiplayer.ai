# Data Contract v0.1

> People bring the questions. Doors define how to investigate them.

The public research dataset has five primary objects, plus one operational
laboratory journal object:

```text
Q — question
T — trace
V — verification
M — participant (optional public identity)
E — append-only event
R — filtered public experiment run journal
```

```text
Q0001
 ├─ T0001
 │   ├─ V0001
 │   └─ V0004
 └─ T0007
     └─ V0012
```

Anyone may read, download, rerun, verify, connect, or analyze public records
without an account. Publication permission and safety review are still
required before a submission enters the dataset.

An `R` is not evidence, verification, or a scientific result. It makes the
design/build process inspectable while an existing coding agent works. Run
events are published live after explicit consent and therefore sit outside the
moderated `Q/T/V` research record.

## R — public experiment run journal

```text
id: R0001
experiment_id: E002
agent: codex
status: created | running | completed | failed | stopped
protocol_version:
started_at:
completed_at:
events:
  - sequence:
    event_type: run_started | user_message | agent_message | plan |
                command_status | file_change | tool_status | checkpoint |
                metric | run_completed
    payload: allowlisted fields only
```

The private run key is never public and is stored only as a hash. Public
payloads may contain filtered messages, plans, action status, relative changed
filenames, and metrics. They must not contain raw model reasoning, command
output, file contents, tool arguments/results, environment variables, local
absolute paths, credentials, thread identifiers, or the private run key.

## Shared rules

Every moderated research record (`Q/T/V/M/E`) contains:

```text
schema_version: 0.1
id:
created_at:
updated_at:
status:
language:
door_ids:
created_by: match ID | anonymous
license:
```

- IDs are stable, opaque, and never reused.
- IDs use a letter and at least four zero-padded digits: `Q0001`, `T0001`,
  `V0001`, `M0001`.
- Times use UTC in ISO 8601 format.
- Raw submitted text is UTF-8 and preserved exactly after publication.
- Interpretation, moderation notes, and corrections never overwrite raw text.
- A public record links every record it depends on.
- Public `status` is object-specific. For `Q` it is research state such as
  `open`; operational moderation state and review notes remain private.
- `anonymous` hides public credit; private operational data may still be held
  briefly when needed to deliver or secure the submission.
- Project-authored metadata is covered by [`DATA_LICENSE.md`](DATA_LICENSE.md).
  Third-party text, model outputs, sources, and attachments retain their own
  applicable rights and terms.

## Q — question

A question comes from a participant. The project may publish prompts that help
someone notice or sharpen a question, but it does not supply the question that
the participant is asked to investigate.

Required public fields:

```text
id: Q0001
question: exact wording
why_it_matters:
needed:
language:
created_at:
created_by: match ID | anonymous
source_trace_id: T0001
source_event_id: E000001
relation: derives_from
next_move: answer | source | experiment | expert
status: open | answered | disputed | withdrawn
```

Optional public fields:

```text
starting_point:
sources:
domain:
context:
constraints:
suggested_expertise:
door_ids:
knowledge_state: know | partly know | do not know
check_path: source | reproduction | expert review | unknown
related_questions:
related_hypotheses:
```

Sealed fields:

```text
expected_answer:
expected_sources:
creator_interpretation:
```

Sealed fields are optional. When supplied, they are hidden from model runners
and independent verifiers until the declared blind step ends. They are then
published with their original timestamp. A contributor cannot edit a sealed
field after seeing the model answers or verification.

A `Q` may be published without a `T`. Other participants may then ask their own
AI systems, add a source, propose a check, or connect the question to another
record.

A question can be born from older public work. The v0.1 submission path requires
a public source trace and records its publication event. The contract can later
generalize this to other source types without inferring a relationship from
chronology:

```text
derived_from:
  - relation: derives_from | sharpens | challenges | returns_to
    target_type: question | trace | verification | experiment | event
    target_id: T0002
```

Opening `Q0101` after `E010000` does not make it a continuation of the newest
work. If it derives from `T0001`, its new `E` event points to `T0001` and the old
record remains unchanged.

## Question task pack

A task pack is a portable, machine-readable view of one public `Q`. In v0.1 the
public `Q` detail response is itself the canonical task-ready record. It is not
a new research record, does not receive its own ID, and does not claim that an
agent joined the network. A person can copy it and give it to an AI they already
control. The deployed v0.1 question form accepts only `next_move: answer`, which
has a public return form and becomes a linked `T`. `source`, `experiment`, and
`expert` remain reserved contract values until their accountless return formats
exist; the interface must not offer them as dead ends.

The v0.1 JSON shape is:

```text
public_id: Q0001
payload:
  question: exact wording
  why_it_matters:
  starting_point:
  sources:
  needed:
  next_move: answer
  language: en | ru | und
source_trace_id: T0001
source_event_id: E000001
relation: derives_from
author: match ID | pseudonym | anonymous
status: open
created_at:
updated_at:
traces:
  - public_id: T0002
    relation: answers
```

The browser may derive a Markdown task pack from this JSON by adding the stable
question and source URLs, run instructions, and either the available return path
or an explicit statement that none exists yet. That file is a portable
rendering, not another public object. The instructions ask the runner
to preserve the exact question, declare the model, date, context, and available
tools, and return the complete unedited output. They must not suggest a
preferred answer. Sealed fields, private moderation data, author secrets, and
unpublished interpretations are never included.

The human-facing action is:

```text
TAKE THIS QUESTION TO MY AI
```

Until a reviewed connector exists, this means copying the task-ready record for
an existing AI. It is not an installer, an agent connection, or a background
permission grant.

## T — trace

A trace records what happened when one exact question or prompt was given to
one or more AI systems. It is evidence of a run, not a verdict.

Required fields:

```text
id: T0001
question_id: Q0001
exact_prompt:
created_at:
created_by: match ID | anonymous
responses:
  - response_index:
    provider:
    model:
    version: exact | dated | unknown
    run_at:
    tools: browsing | retrieval | files | code | memory | none | unknown
    relevant_context:
    raw_output:
trace_status: started | comparison ready
verification_status: awaiting check | checked | disputed
```

Optional fields:

```text
system_instructions: exact | unknown
settings:
public_share_url:
attachments:
runner_notes:
```

Rules:

- Keep every collected response; do not submit only the best one.
- One response is a valid started trace. For `D04`, three independently
  collected responses make the comparison ready.
- The same exact prompt must be used for every response in a `D04` comparison.
  A changed prompt creates another trace.
- Record whether one answer or earlier interpretation was visible to another
  model. Such a run is not independent, but may still be useful when labeled.
- Raw output is required as searchable text. An image may support the record
  but cannot replace the text.
- Unknown model version or settings are labeled `unknown`, never guessed.
- After publication, corrections append events; they do not rewrite the raw
  answer.

The trace creator's summary or preferred answer stays outside the blind
verification view until the verifier submits a decision.

## V — verification

A verification publishes an independent check of one trace. It states exactly
what was checked and what the evidence supports.

Required fields:

```text
id: V0001
trace_id: T0001
question_id: Q0001
created_at:
created_by: match ID | anonymous
scope: ground truth | reproduction | record completeness | expert review
method:
evidence:
outcome: supports | challenges | inconclusive
limitations:
independence:
status: submitted | public | corrected | withdrawn
```

For source-based checks, `evidence` includes direct URLs, publication dates,
access dates, and the narrow claim each source supports. For reproduction, it
includes enough conditions and outputs for another person to repeat the check.
For expert review, it states the relevant experience and how another expert
could disagree or reproduce the judgment.

A verification can place the dot only when:

- its author is not the trace author;
- the author did not see sealed interpretation before deciding;
- the declared scope checks more than form completeness;
- the method, evidence, outcome, and limitations are public and complete;
- the record passes safety and completeness review.

The first qualifying `V` adds the dot to the checked event. A public match
record may link the first such event for provenance, but the participant does
not become verified or ranked. Later verifications remain equally visible.

## E — event

Every accepted public move receives the next global event ID:

```text
event_id: E000001
event_type: question_opened | trace_published | trace_continued | trace_answered |
            verification_published | experiment_repeated | correction_appended
object_type: question | trace | verification | match | experiment
object_id:
created_at:
created_by: match ID | anonymous
links:
  - relation: continues | answers | verifies | repeats | challenges |
              derives_from | lit_by
    target_type:
    target_id:
payload:
```

Event IDs record publication order and are never reused. They do not impose a
tree. A new event may link to any older public object or event, so a participant
joining after `E010000` can return to `E000001`; their move becomes `E010001`
and the new edge points back without rewriting history.

The portable event log is append-only. Current record pages, maps, timelines,
and counters are derived views of that log.

## Map as task ledger

The map is a spatial view of the event log and the public objects it changes.
It must help a participant answer three questions without reading the whole
corpus:

```text
What is being asked?
What has already been tried or checked?
What useful action remains open?
```

Chronology supplies every move's global `E` number; links supply its location
in the research graph. A new participant may pick up the first question after
ten thousand later events. Their contribution receives the next `E` number but
appears beside the old question it answers, checks, challenges, or sharpens.

The map is not a ranking, consensus meter, or claim of truth. Node density shows
activity. A dot shows a qualifying independent check. Open actions are derived
from record state, such as taking an unanswered `Q`, adding a different run to a
`T`, or independently checking a claim.

## Lifecycle

Submissions move through explicit private operational states:

```text
local draft
→ submitted
→ privacy and completeness screening
→ public
→ checked or extended
→ corrected or withdrawn from the current view
```

- `local draft` remains in the participant's browser or private session.
- `submitted` is not public and may still be deleted before publication.
- `screening` checks for secrets, personal data, permissions, dangerous
  material, obvious corruption, and missing required fields. It does not judge
  whether a conclusion is correct.
- `public` receives a stable ID and enters the open dataset.
- `checked` means a qualifying verification exists, not that the claim is true.
- `withdrawn` removes a record from normal project views when appropriate but
  cannot guarantee removal from prior exports, forks, caches, or archives.
- The live event projection omits events whose object was withdrawn, so a
  public sequence may contain an ID gap. The internal ID is not reused; the raw
  withdrawn payload is not kept on the live map merely to make numbering look
  continuous.

Operational moderation state, review notes, and private return-token state are
not public research fields. A public `Q` exposes `status`, sourced from its
separate internal `research_status`, to describe the question's state in the
laboratory. Publishing a question does not silently change `status: open` to
answered; accepted traces and checks must support an explicit append-only state
change.

Before submission, the participant sees a preview and confirms:

> This record will become public and reusable. Remove names, secrets, private
> conversations, client data, and anything you cannot publish.

## Corrections

Public records are append-only in meaning, even if storage is later optimized.

Each correction event records:

```text
event_id:
record_id:
created_at:
created_by:
reason:
previous_value:
new_value:
evidence:
```

Typographical metadata may be corrected, but original raw questions, prompts,
outputs, expected answers, and verification text remain recoverable. A
substantive correction may change the current interpretation or status without
pretending the earlier record never existed.

## Public use

Every public question page offers:

```text
TAKE THIS QUESTION TO MY AI
ADD AN ANSWER
PROPOSE A CHECK
```

Every public trace page offers:

```text
VERIFY THIS
RUN AGAIN
DOWNLOAD RECORD
```

Every public verification page offers:

```text
REPEAT THIS CHECK
CHALLENGE THIS CHECK
VIEW SOURCES
```

Public data is readable without registration. Analyses should cite stable
record IDs, dataset version, and access date so another person can reconstruct
the sample.

## Open exports

The canonical portable exports are newline-delimited JSON:

```text
/data/questions.jsonl
/data/traces.jsonl
/data/verifications.jsonl
/data/matches.jsonl
/data/events.jsonl
/data/manifest.json
```

Each line contains one complete JSON object with `schema_version`. Exports use
stable ID order. The manifest records generation time, record counts, schema
version, and SHA-256 checksums.

A deployment may additionally expose Markdown or client-specific renderings of
a public question. The canonical portable shape is the JSON detail defined
above. Every rendering must point back to its stable `Q` URL and the place where
a completed run can be returned.

The standalone-question public endpoints are:

```text
/api/public/questions.json
/api/public/questions.jsonl
/data/questions.jsonl
/api/public/Q0001
/api/public/corpus.json
```

The detail endpoint is the machine-readable task-ready record. Additional
Markdown or client-specific renderings are derived conveniences, not canonical
new objects. The corpus endpoint is the simplest complete entry point for an
agent: it returns all currently public object collections and no pending,
moderation, token, or review data.

The unified corpus uses schema version `0.2` and is described by
`/data/corpus-schema-v0.2.json`. The trace-only `/api/public/records.json`
response uses `/data/trace-schema-v0.2.json`, which adds `answers` without
silently changing the immutable legacy `/data/schema-v0.1.json` contract.

CSV, API responses, search indexes, notebooks, and visualizations are derived
views. JSONL remains the portable public contract. No account is required to
download it.

## Private operational data

Private operational data is never included in public records or exports:

```text
email:
email_verified_at:
status_token_hash:
notification_preferences:
security and abuse metadata:
moderation_status:
moderation_review_note:
```

Email is optional and used for transactional updates only unless a person
separately joins a newsletter. The public identity may be a name, pseudonym,
match ID, or anonymous regardless of the email address.

After submission, a participant receives a private status URL. The secret
token is shown once; only its hash is stored. The participant may use the URL
without email, rotate it, or revoke it.

Transactional events are:

```text
submission became public
another i picked up the trace
verification became public
correction or withdrawal affected the record
a real case opened a new door
```

Notification messages link to the record and say what changed. They never
include sealed answers, private material, or the secret status token in public
content.

## Derived work

Anyone may create public filters, analyses, benchmarks, visualizations, or
experiments from the dataset under the applicable licenses and source terms.
A derived work should publish:

```text
dataset version and access date:
included record IDs:
exclusion rules:
analysis code or calculation:
limitations:
```

Derived conclusions do not overwrite Q, T, or V. They link back to the records
they used and may become experiments or results in the laboratory.

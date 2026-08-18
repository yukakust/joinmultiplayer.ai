# Data Contract v0.1

> People bring the questions. Doors define how to investigate them.

The public dataset has three primary objects:

```text
Q — question
T — trace
V — verification
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

## Shared rules

Every record contains:

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
domain:
language:
created_at:
created_by: match ID | anonymous
door_ids:
knowledge_state: know | partly know | do not know
check_path: source | reproduction | expert review | unknown
status: open | answered | disputed | withdrawn
```

Optional public fields:

```text
context:
constraints:
suggested_expertise:
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

The first qualifying `V` sets `dotted_by` on the trace author's public match
record. Later verifications remain equally visible. A verification does not
automatically dot its own author.

## Lifecycle

Submissions move through explicit states:

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
ASK MY AI
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

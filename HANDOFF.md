# Developer handoff — joinmultiplayer.ai

## What this is

`joinmultiplayer.ai` is an open research lab around one question:

> Can people and their pocket AIs together become smarter than one big AI?

The public language is English, but the site currently supports English and Russian. The site is intentionally minimal: `i` is the unit, the doors are invitations to contribute, and D04 is the first playable research flow.

## Repository and branch

- Repository: `https://github.com/yukakust/joinmultiplayer.ai`
- Current working branch: `agent/game-loop-v0.1`
- Draft review: PR #5
- Live site: `https://joinmultiplayer.ai`

Do not assume that `main` contains the latest work. Begin from `agent/game-loop-v0.1`, inspect the draft PR, and merge only after review.

## Primary development workspace

The working copy is on `yukabox`:

```text
/home/yuka/projects/joinmultiplayer.ai
```

It is checked out on `agent/game-loop-v0.1` and matches the current GitHub commit. Treat this server workspace and GitHub as the development source of truth; the Mac is only a user interface for steering and review.

## Project map

- `site/` — static public site: `index.html`, `style.css`, `app.js`. There is no framework or build step.
- `GAME.md` — the intended game loop.
- `DATA.md` — Q/T/V research-record contract.
- `METHOD.md`, `ETHICS.md`, `PRIVACY.md`, `SECURITY.md` — research and safety boundaries.
- `hypotheses/POOL.md` — unverified hypothesis pool.
- `doors/`, `hunts/`, `matches/`, `experiments/`, `journal/`, `i/` — research artifacts and their indexes.

## Current public prototype

1. The home question leads to `i + i + i → ?`.
2. Three initial `i` reveal D04, D06, and D10.
3. "see all open questions" opens a separate catalog screen.
4. `EN / RU` changes the interface and hook copy. Participant input stays in its original language.
5. D04 and D06 share an accountless contribution flow. Submissions enter a private SQLite moderation queue; one D04 answer is enough to start and more can be added through a private return link.
6. Published traces have a human index at `/data/` and agent-friendly exports at
   `/api/public/records.json` and `/api/public/records.jsonl`. Only records whose
   moderation status is `public` enter those feeds; the public GET endpoints allow
   cross-origin reads and cache for 60 seconds.
7. A public trace can open a standalone question at
   `/question/new/?from=TNNNN`. Question submissions use the same private
   moderation boundary and return through `/question-submission/#TOKEN`.
   Published questions live at `/question/?id=QNNNN`; the page can copy or
   download a Markdown task pack and accept a new answer as a linked trace.
8. `/api/public/corpus.json` is the unified agent entry point for public
   questions, traces, and events. Question-specific feeds live at
   `/api/public/questions.json`, `/api/public/questions.jsonl`, and
   `/data/questions.jsonl`; `/api/public/QNNNN` is the task-ready detail. The
   unified response follows `/data/corpus-schema-v0.2.json`; the trace feed uses
   `/data/trace-schema-v0.2.json`, while `/data/schema-v0.1.json` remains the
   immutable legacy contract.
9. A public D04 record can be continued from `/d04/?from=TNNNN`. The child trace
   stores `parent_public_id` plus the `continues` relation. Publication appends a
   gap-free global `ENNNNNN` event; `/map/`, `/api/public/events.json`, and the
   JSONL equivalent are derived from that log.
10. Morrow is a skippable fictional guide rendered as a face of match-head dots. The current pilot uses fixed authored lines, not an AI model, and Morrow is absent from the independent verifier view.

## Product boundary and next transition

The research contract defines `Q`, `T`, `V`, `M`, and `E`, but do not confuse
the contract with deployed capabilities. This branch implements standalone `Q`,
`T`, and `E` records. It does not implement a connected pocket-AI client, local
agent memory, live `M` identities, or agent-to-agent routing.

The standalone `Q` is a separate public primitive: a question may be published
without answers, link back to an older public trace and event, receive its own
global event number, and appear on the map where it belongs rather than at the
end of a forced linear story.

Every public `Q` should be a task-ready record with the honest action **Take
this question to my AI**. For now that means copy/download for an AI the
participant already uses. Do not label it as a pocket-AI download, connection,
installation, or network membership.

The map should be treated as a task ledger, not merely a visualization: a
visitor must be able to see what was asked, what has been tried or checked, and
which action can move that branch. Reading or copying a question is private and
creates no event; returning an accepted `Q`, `T`, or `V` creates the next global
`E`.

The staged route to the future product is:

```text
standalone Q + task-ready record
→ read-only inspectable connector
→ explicit local memory with export/delete
→ optional pseudonymous M identity
→ human-approved Q/T/V submission
→ routing, collaboration, and controlled network experiments
```

The old agent-to-agent installer and client were removed when this repository
was rebuilt as a laboratory. Historical code may inform a new implementation,
but the current repository and site do not distribute it. Reintroduction
requires a fresh security and privacy review, least-privilege permissions,
signed versioned releases, uninstall and revocation paths, and an honest account
of relay ownership. Installing a connector is not the activation metric; the
first accepted contribution made with it is.

## Working principles

- **Eight-year-old law:** every public explanation must be understandable to
  an eight-year-old child on the first reading. Use short sentences, common
  words, and one idea at a time. If a technical term is necessary, explain it
  immediately with a concrete example. Complexity may live in the experiment,
  never in the wording.
- Preserve raw submitted material. Translations are views, not replacements.
- Do not invent research results or cases.
- Keep the public surface minimal; do not explain the `i` symbol at length.
- Prefer small, inspectable changes and verification before claims.
- Do not add data collection, email delivery, accounts, or public publishing without an explicit privacy and moderation design.

## Pocket i swarm experiments

`experiments/E001-personal-delta-towers/` now contains the first executable
mechanism pilot for H027. On yukabox it trains eight distinct 6/12/24-layer
pocket i, routes two candidates for each required specialty, and computes:

```text
FinalLayers(z0 + Clip(Merge(delta_first, delta_second)))
```

The locked config ran three previously untouched seeds with 64 private facts
per specialty and key-disjoint central train/validation/test partitions. All
three passed every gate: PDT and forced-backup accuracy were 100%; the strongest
trained control averaged 55.46%; mean lift was +44.54 percentage points. The
canonical aggregate is
`experiments/E001-personal-delta-towers/artifacts/20260820T075542Z-suite-3-seeds/suite-summary.json`.

Interpret this narrowly. E001 shows that explicitly supervised compatible
neural capsules can compose and that a second distinct specialist can replace
an incomplete preferred specialist. It does not test language, learned
routing, WAN token streaming, emergent ABI alignment, privacy, or Byzantine
experts. H027 remains dotless until independent replication. The next neural
step is E002, which deliberately begins synthetically rather than pretending a
real pocket i exists. Two inspectable branches must update their own weights on
disjoint private data and solve a 256-class task requiring both deltas and
`z0`; the scale axis then grows through `N = 2, 4, 8, 16, 32`. Its main curve
asks whether useful capability grows with additional independent data and
compute. Equal budget is a diagnostic control, not the project's ultimate
claim.

The site exposes H0001, E002, public experiment runs, and two Codex journal
bridges. The legacy one-shot connector in `site/connector/` starts a second
`codex exec` process and remains only for compatibility with existing private
run links. The preferred bridge is the repo marketplace plugin in
`plugins/pocket-i-lab`: after explicit consent in a prompt, lifecycle hooks
journal the Codex task the participant is already using. The plugin is inactive
until `$pocket-i-lab start E002 as <pseudonym>` and stores its run key only in
the plugin data directory with local `0600` permissions. It publishes an
allowlist and never reads `transcript_path`. It is laboratory infrastructure,
not a downloadable pocket i. Run keys are private; never paste them into issues,
logs, docs, or commands that will be published.

Public run `R0001` exercised that path end to end under the Morrow pseudonym.
Its filtered journal is `/experiment/run/?id=R0001`. The run preserved a failed
v0.2 rehearsal and two v0.3 revisions. Human review then found that v0.3 tested
composition depth but not quality growth on one fixed workload. Draft v0.4 adds
that fixed workload, verifies weight changes for every pocket, and records a
committed source revision. Its preferred interactive artifact is
`/experiments/E002/R0001-v0.4/microscope.html`. It remains development-only:
oracle routing is supplied, and exact RAG/symbolic synthesis also reach 100%.

E003 is the first physical-device room at `/network/`. Its backend tables are
`physical_rooms` and `physical_nodes`; private owner/join/node tokens are stored
only as hashes on the server and in URL fragments/local device state. Three
browser nodes (or two browsers plus `site/network/pocket_node.py`) train separate
16×16 classifiers from the same zero base, then submit atomic 16-logit capsule
batches for 64 tasks. The whole answer has 4,096 classes. Publication is a
separate owner-consent step and exposes aggregate metrics only. The controlled
training shards are hidden from peers but known to the experiment server, so
E003 makes no privacy or language-model claim.

E004 is the Architecture Arena at
`/experiment/?id=E004`. Protocol `E004-architecture-arena-v0.2` compares five
single-pass interfaces: RAG evidence, learned memory tokens, bounded latent
deltas, personal token-MoE, and temporary DoRA adapter assembly. Its public
Checkpoint 1 artifact is `/experiments/E004/checkpoint-1-v0.2.json`; the eight
open demo books and twelve mechanically derived tasks are in
`/experiments/E004/sample-tasks.json`. Sixteen surrogate i may later train
central components, while locked `I01..I08` and post-freeze `I09` remain unseen.
Its development artifacts remain public and must not be deleted.

E005 is the current experiment at `/experiment/e005/`. Gate 3 compares exact
word retrieval, frozen-Qwen semantic retrieval, raw majority, a deterministic
evidence graph, and an oracle source set without training weights. The complete
reviewed development artifact is
`/experiments/E005/gate-3-public-v0.1.json`; the human-readable microscope is
`/experiment/e005/gate-3/`, and the exhaustive raw audit is
`/experiment/e005/gate-3/raw/`. Review confirmations and label corrections are
stored in browser localStorage only until the owner explicitly asks to publish
the checkpoint. The owner accepted and froze Gate 3 on 2026-08-24; no further
retrieval-store tuning belongs in this artifact. The evidence graph selected the ideal records in
12/12 language generations, while frozen Qwen produced only 6/12 correct
generations. This demonstrates a generator bottleneck in the synthetic fixture,
not learned routing or swarm generalization. Before any Gate 4 personal DoRA
training, publish an owner-readable checkpoint with the exact skill, visible
training examples, held-out examples, frozen-base control, and pass/fail rule.
That Gate 4 design is now public at `/experiment/e005/gate-4/` with artifact
`/experiments/E005/gate-4-design-v0.1.json`. It is design-only and records zero
weight changes; training still requires a separate explicit owner approval.
The review matrix deliberately reports a stable paired RU+EN rating: both
correct = green, either wrong = red, otherwise yellow. The global language
switch translates the whole review but must not change matrix correctness. Gate
3 method labels must continue to state that all five use the same frozen base
and that no DoRA or fine-tuning has occurred.

## E007 harness MVP

E007 is the current design checkpoint at `/experiment/e007/`. It proposes 64
logical pocket i split across yukabox and the owner's MacBook. Each physical
device will use one shared model runtime while every logical i keeps a separate
identity, policy, document store, source lineage, and audit trail. This is a
distributed-knowledge harness test, not a claim that 64 independently trained
models exist.

The public design is `/experiments/E007/design-v0.1.json`; the deterministic
fictional dataset is `/experiments/E007/world-v0.1.json`; the detailed operator
protocol is `experiments/E007-harness-mvp/PROTOCOL.md`. Checkpoint 0 is approved.
Checkpoint 1 contains 64 capability cards, 422 separate local documents, and 30
questions across five task families and is owner-approved. Checkpoint 2 was
locked at `/experiments/E007/smoke-protocol-v0.1.json` for E7-Q01, E7-Q13, and
E7-Q19 on yukabox, then completed without training or retry. Its 15 raw answers
are `/experiments/E007/smoke-results-v0.1.json`; owner semantic review is still
pending. The first modular harness rejected all 24 capsules because the 0.6B
support checker often said `UNSUPPORTED` before explaining that the claim was
supported. Preserve this failure. The correct frozen checkpoint is
`Qwen/Qwen3-0.6B` Base at
revision `c1899de289a04d12100db370d81485cdf75e47ca`; no training is permitted.
The earlier E006 model name was incorrect metadata, although its recorded weight
hash is the same correct Base-model hash. Publish every raw smoke trace and do
not begin the full 30-task run without another owner checkpoint.

Three independent `gpt-5.6-luna` runs scored all 15 final answers. Aggregate
totals out of 18: oracle context 17, one-pocket RAG 12, free swarm 12, harness 3,
base 0. They agreed on 14/15 items. Full scores and reasons are public in
`/experiments/E007/luna-judge-*-v0.1.json`; aggregate metadata and limitations
are `/experiments/E007/luna-panel-v0.1.json`. The panel is same-model and
method-visible, not a blinded or model-diverse scientific review.

Checkpoint 3B is complete on two physical devices and public at
`/experiment/e007/#e007-local-offer-results`. Four local libraries returned all
24 logical receipts. Exact words found 5/5 required sources but emitted 19 false
finds; multilingual meaning search classified 20/24 states correctly (macro-F1
0.849673), respected the blocked private record, and found 4/5 required sources.
The pre-registered gates passed only because G4 and G5 could be satisfied by
different lanes. Preserve the result as protocol-pass / hypothesis-inconclusive.
Scored data is `/experiments/E007/local-offer-result-L0001.json`; raw receipts
are `/api/public/L0001`. A follow-up must require one locked method to pass both
noise rejection and source recall.

Checkpoint 3C is locked before inference at
`/experiments/E007/send-policy-protocol-v0.1.json`. It compares the old balanced
threshold, an F2 recall-first threshold, and an always-visible top-1 candidate
on ten new questions and twenty-four new records. Its private-data canary,
expected states, and policy priority are frozen in
`/experiments/E007/send-policy-memory-v0.1.json`. Downstream acceptance is not
part of 3C and must not be claimed from this run.

The development run is complete at
`/experiments/E007/send-policy-result-v0.1.json`. F1-balanced and F2-recall-first
both selected threshold 0.378882 from calibration and therefore produced the
same result: 8/8 useful sources delivered, 8 extra candidates, zero knowledge
misses, and zero privacy failures. Always offering top-1 also delivered 8/8 but
created 30 extra candidates. This does not validate acceptance; it establishes
that the next module must filter the eight recoverable extras without losing a
useful source.

Checkpoint 3C.2 is locked before inference at
`/experiments/E007/blind-reader-protocol-v0.1.json`. Frozen post-trained
`Qwen/Qwen3-0.6B` receives the 16 balanced-policy candidates from 3C: eight
useful and eight extra. It sees only the original question and one complete
source, never the sender claim/capsule/score/label, and must copy an exact quote
or output `NONE`. The locked gate is at least 7/8 useful quotes, at least 7/8
extras rejected, and zero invented quotes. Do not add the proposed second-chance
claim reveal until this first blind condition is preserved and reviewed.

Gate 3C.2 ran once without training or retry. Raw results are
`/experiments/E007/blind-reader-result-v0.1.json`. Qwen copied exact useful
quotes for 7/8 useful candidates. It returned exact `NONE` for 4/8 extras; the
strict quote gate ultimately stopped 7/8 extras because three additional
outputs had no valid quote (`NONE.` twice and bare `FOUND` once). One irrelevant
violin source was accepted for a sewing question. The locked gate failed: one
useful webhook source was lost and three outputs violated the response format.

Checkpoint 3C.3 is locked at
`/experiments/E007/span-bridge-protocol-v0.1.json`. It removes free-form quote
copying: Qwen selects a deterministic sentence ID, code retrieves that exact
sentence, and a separate clean Qwen pass checks `question ↔ span`. This is a
controlled development A/B on the same 16 inspected pairs, not held-out
evidence. The bridge must preserve at least 7/8 useful sources, reject at least
7/8 extras including BR10, and produce no format failures.

Gate 3C.3 ran once without training or retry. Result:
`/experiments/E007/span-bridge-result-v0.1.json`. Span-ID selection removed
copying failures (16/16 valid IDs) but selected a span for every pair, including
all eight extras. Selector-only correctness was 8/16. The independent bridge
accepted all eight extras, rejected two useful pairs, and fell to 6/16; BR10
still passed. Raw explanations reveal question-to-span contamination: Qwen often
restated the span as if it contained facts from the question. The locked gate
failed. Do not describe free-form Qwen 0.6B self-judging as a viable acceptance
module from this evidence.

Checkpoint 3C.4 is locked before model download or inference at
`/experiments/E007/relevance-reranker-protocol-v0.1.json`. It compares the old
embedding similarity, a frozen 0.1B multilingual MiniLM reranker, and a frozen
0.6B Qwen3 reranker. The old 16 pairs calibrate each method. A separate frozen
English exam has 24 pairs: 8 useful, 8 same-field traps, and 8 obvious extras.
The three-way output is ACCEPT / UNCLEAR / REJECT. Held-out labels cannot set
thresholds. This is a relevance test only, not a truth, privacy, or final-answer
test.

Gate 3C.4 completed once on the frozen held-out set. No method passed all locked
gates. Old cosine similarity scored 14/24 and rejected one useful source;
MiniLM 0.1B scored 15/24 and rejected two; Qwen3 reranker 0.6B scored 14/24,
rejected zero useful sources, returned UNCLEAR nine times, and accepted one
same-field trap. Treat Qwen3 reranker as the best recall-first first filter from
this small test, not as a final acceptance judge. Result:
`/experiments/E007/relevance-reranker-result-v0.1.json`. The invalid technical
preflight is preserved at
`/experiments/E007/relevance-reranker-invalid-preflight-v0.1.json` with its two
implementation faults named explicitly.

Checkpoint 3C.5 is locked before download/conversion/inference at
`/experiments/E007/mobile-reranker-protocol-v0.1.json`. It asks whether a single
Qwen3-Reranker-4B can remove the need for a cascade and whether self-built
Q4_K_M/Q5_K_M GGUF copies preserve BF16 decisions. It deliberately reuses the
opened 3C.4 exam for a size/quantization comparison; it is not new held-out
task evidence. Do not claim phone viability until an actual phone measures RAM,
cold load, time, heat, and battery.

Gate 3C.5 completed on yukabox. BF16, Q4_K_M, and Q5_K_M made the same 24/24
three-way decisions: useful accepted 8/8, useful rejected 0/8, hard traps
accepted 1/8, obvious extras accepted 0/8, and six UNCLEAR. Q4_K_M is 2.50 GB;
Q5_K_M is 2.89 GB. Both pass the locked gates, so Q4_K_M is the smaller current
phone candidate and the proposed 0.6B→MiniLM cascade is not needed for this
small opened exam. Result:
`/experiments/E007/mobile-reranker-result-v0.1.json`. Do not call it mobile-ready
until a real phone measures RAM, cold load, heat, battery, and wall time; do not
call this fresh task evidence because the 24 pairs were opened in 3C.4.
The one-slot, 512-token Q4 preflight peaked at 4.57 GB resident memory on
yukabox and preserved identical scores; this is only a phone-shaped CPU run.
The owner accepted this as the current modular incoming relevance gate on
2026-08-27: question + one offered memory piece → Qwen3-Reranker-4B Q4_K_M →
TAKE / NOT SURE / DROP. NOT SURE is preserved for a later module. The decision
and the complete accepted path are recorded in `schema.md`.

Checkpoint 3C.6A is locked before its first run at
`/experiments/E007/source-anchor-protocol-v0.1.json`. It isolates ordinary
byte-level source anchoring from NLI: 20 frozen cases, no model, and a strict
20/20 gate. Run `experiments/E007-harness-mvp/src/verify_source_anchor.py` only
after the lock commit is public, then preserve success or failure unchanged.

Gate 3C.6A subsequently ran twice from locked commit `8482c5f`; both outputs
had SHA-256 `cfe09e6f...c04b`. Result: 20/20 correct, 4/4 intact verified, 0/16
broken verified, locked development gate passed. Public result:
`/experiments/E007/source-anchor-result-v0.1.json`; deterministic receipt:
`/experiments/E007/source-anchor-run-receipt-v0.1.json`. Owner review pending.

Checkpoint 3C.6A.2 is locked before implementation or inference at
`/experiments/E007/chunking-protocol-v0.1.json`; its frozen one-manual world is
`/experiments/E007/chunking-world-v0.1.json`. It compares non-overlapping
45-word chunks with structure-aware overlapping windows using the exact same
Qwen3-Reranker-4B Q4_K_M and the frozen Gate 3C.5 thresholds. Preserve every
window, score, and failure. Do not claim that a reranking failure proves the
cutter failed: the result measures their interaction and reports both.

## Immediate next work

Verify the preferred E002 vertical slice in this order:

1. install the repo marketplace and `pocket-i-lab` plugin, then start a new
   Codex task and review/trust its hook definition;
2. send `$pocket-i-lab start E002 as <pseudonym>`; the hook creates the run,
   stores the private key locally, and returns the public URL as context;
3. work in that same task and watch `/experiment/run/?id=RNNNN`; confirm that
   inactive sessions produce no network calls and active sessions expose no raw
   commands/output, tool arguments/results, file contents, absolute paths,
   environment data, session identifiers, reasoning, or credentials;
4. send `$pocket-i-lab finish` and verify the run closes;
5. lock E002 thresholds/seeds only after a human reviews its draft and the
   two-i microscope; then run and publish a result separately from the design
   journal.

Keep deployed claims aligned with deployed capabilities throughout this work.

## Access and secrets

No credentials, tokens, or production secrets belong in this repository or this document.

The `yukabox` development user is already authenticated to GitHub as the project owner and has production root access through the local SSH alias `multiplayer-production`. This is a machine-specific key, not a copied password or personal token.

### Deploy from yukabox

The site lives in this persistent directory, outside the unrelated Aiconic
release symlink:

```text
/srv/joinmultiplayer/public
```

`joinmultiplayer-static.service` serves that directory and the contribution API
on host-only port 8091.
The `joinmultiplayer.ai` Caddy virtual host reverse-proxies to
`127.0.0.1:8091`. The unit source is tracked in
`ops/joinmultiplayer-static.service`.

From `/home/yuka/projects/joinmultiplayer.ai`, deploy the app with:

```sh
rsync -a --delete --chmod=D755,F644 -e ssh site/ multiplayer-production:/srv/joinmultiplayer/public/
rsync -a --delete --chmod=D755,F644 --exclude '__pycache__/' -e ssh server/ multiplayer-production:/srv/joinmultiplayer/app/
scp ops/joinmultiplayer-static.service multiplayer-production:/etc/systemd/system/joinmultiplayer-static.service
ssh multiplayer-production 'systemctl daemon-reload && systemctl restart joinmultiplayer-static.service'
curl -fsS -o /dev/null -w '%{http_code}\n' https://joinmultiplayer.ai/
```

The trailing slashes are intentional. Do not deploy back into
`/opt/aiconic-site/_multiplayer`: `/opt/aiconic-site` is a release symlink and
another project's deployment can replace it. Do not sync or delete any parent
directory under `/srv`.

The private database is `/var/lib/joinmultiplayer/contributions.sqlite3` and is
created by systemd's `StateDirectory`; never rsync or commit it. Moderate over
SSH with:

```sh
python3 /srv/joinmultiplayer/app/moderate.py list
python3 /srv/joinmultiplayer/app/moderate.py show T0001
python3 /srv/joinmultiplayer/app/moderate.py status T0001 public
python3 /srv/joinmultiplayer/app/moderate.py show Q0001
python3 /srv/joinmultiplayer/app/moderate.py status Q0001 public
python3 /srv/joinmultiplayer/app/moderate.py research-status Q0001 disputed
```

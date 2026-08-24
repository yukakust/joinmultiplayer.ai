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
the checkpoint. The evidence graph selected the ideal records in
12/12 language generations, while frozen Qwen produced only 6/12 correct
generations. This demonstrates a generator bottleneck in the synthetic fixture,
not learned routing or swarm generalization. Gate 4 personal DoRA procedure
training must not begin until the owner visually reviews Gate 3.
The review matrix deliberately reports a stable paired RU+EN rating: both
correct = green, either wrong = red, otherwise yellow. The global language
switch translates the whole review but must not change matrix correctness. Gate
3 method labels must continue to state that all five use the same frozen base
and that no DoRA or fine-tuning has occurred.

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

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

## Immediate next work

Complete and test the standalone-question loop before adding social mechanics:

1. create a real `Q` derived from `T0002`;
2. moderate and publish it without requiring a model answer;
3. verify its provenance, public status, and task pack;
4. confirm its event appears beside the source branch on the map;
5. take it into an existing AI and return a new trace linked by `answers`.

The deployed v0.1 question form accepts only `next_move: answer`. Keep the wider
contract values hidden until each has an accountless return format.

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

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
6. Morrow is a skippable fictional guide rendered as a face of match-head dots. The current pilot uses fixed authored lines, not an AI model, and Morrow is absent from the independent verifier view.

## Working principles

- Preserve raw submitted material. Translations are views, not replacements.
- Do not invent research results or cases.
- Keep the public surface minimal; do not explain the `i` symbol at length.
- Prefer small, inspectable changes and verification before claims.
- Do not add data collection, email delivery, accounts, or public publishing without an explicit privacy and moderation design.

## Immediate next work

Run D04 with a real question as the first player. Record where the flow causes friction before adding more doors, accounts, maps, or social mechanics.

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
rsync -a --delete -e ssh site/ multiplayer-production:/srv/joinmultiplayer/public/
rsync -a --delete -e ssh server/ multiplayer-production:/srv/joinmultiplayer/app/
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
```

# new/ — the game-shaped front door (new.joinmultiplayer.ai)

This directory is a **separate copy** of the site and server, developed on the
branch `claude/new-ui-week1` and served at https://new.joinmultiplayer.ai.
The production site at the repository root (`site/`, `server/`) is never
modified from here. When the new version wins, the domains switch; until then
both run side by side.

## What it is

joinmultiplayer.ai is an open laboratory testing one question: can many small
personal AIs ("pocket i", living on their owners' own devices) beat one big AI?
Every experiment protocol is pinned before the run and every failure is
published. `new/` wraps that laboratory in a game so that curious engineers can
enter without a manual:

| Route | What a visitor sees |
|---|---|
| `/game/` | The one screen: your pocket i (a robot with mind / body / link slots), who is at the table, the game's current call, one button — make a move. First visit plays the intro: a radio signal → the safehouse terminal (cell record 001) → choose your figurine → your first field run. |
| `/journey/` | The chronicle: every experiment as a point on a map, statuettes for milestones, dead ends kept. Every number links to its raw JSON. |
| `/workbench/` | The body of pocket i as upgradeable parts: what each part is, its frozen record, and a copy-for-your-AI brief to beat it. |
| `/start/` | How this place works, in plain words. |
| `/play/` · `/d04/` | Pick a figurine, take an open question to your AI, bring the whole answer back. Submissions are moderated; when published, your figurine ignites and you get a personal link to light the next person. |

Invite links carry the guest's figurine: `/game/?lit=M0001&piece=lens`. The
terminal then shows their reserved piece and a personal **slot** — a real hole
in the harness MVP with its numbers and raw result JSONs.

The fiction (2040, the Merger, the Answer, the safehouse) lives in
`lore/WORLD-BIBLE.md` and obeys three laws: fiction may only promise the real
roadmap; every number on the site is real and clickable; shadows, not names.

## Layout

```
new/
  site/        static SPA: index.html, app.js (bilingual EN/RU copy dicts), style.css, assets/
  server/      server.py — stdlib HTTP + SQLite (contributions, questions, events, matches);
               moderate.py — CLI moderation
  tools/       seed_q0001.py (mirror the canonical open question, offset id sequences),
               backup_db.py (nightly WAL-safe snapshot), crier.py (Telegram announcer, parked)
  ops/         systemd units: static server, nightly backup timer, crier
  lore/        WORLD-BIBLE.md, POCKET-I-IDENTITY.md
  design/      UI-BRIEF.md, DMG-BRIEF.md (briefs for the designer)
```

## Running locally

```bash
python3 new/server/server.py --site new/site --db /tmp/new.sqlite3 --port 8092
python3 new/tools/seed_q0001.py --db /tmp/new.sqlite3
```

Public reads (corpus, records, questions) come from the production API when the
host is not production; writes (contributions, matches) go to the local DB.
New-server ids start above 100 so they never collide with the public corpus.

## Deploying

The production host runs `new/ops/joinmultiplayer-new-static.service` from
`/srv/joinmultiplayer-new/checkout` (port 8092, Caddy in front with TLS and
gzip). Deploy = `git fetch && git reset --hard origin/claude/new-ui-week1 &&
systemctl restart joinmultiplayer-new-static`. Bump the `?v=` cache-busters in
`site/index.html` when `app.js`/`style.css` change — Cloudflare caches assets.

Moderation: `python3 new/server/moderate.py --db /var/lib/joinmultiplayer-new/contributions.sqlite3 list`
then `status T0101 public`. Backups: `joinmultiplayer-new-backup.timer`, 03:10 UTC,
14 days kept in `/var/backups/joinmultiplayer-new/`.

## Contributing

The game itself is the contribution guide: take a slot on `/workbench/` or in
your terminal, beat the number under the same frozen protocol, and bring the
result as a GitHub issue (`[UPGRADE] <part>`) or a trace. A record changes only
after an independent rerun — no one dots their own item.

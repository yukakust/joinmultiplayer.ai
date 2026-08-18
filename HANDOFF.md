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
5. D04 is a browser-local UX prototype: it records a question, three raw AI answers, an interpretation, identity, and an independent check. It does not publish anything or send email yet.

## Working principles

- Preserve raw submitted material. Translations are views, not replacements.
- Do not invent research results or cases.
- Keep the public surface minimal; do not explain the `i` symbol at length.
- Prefer small, inspectable changes and verification before claims.
- Do not add data collection, email delivery, accounts, or public publishing without an explicit privacy and moderation design.

## Immediate next work

Run D04 with a real question as the first player. Record where the flow causes friction before adding more doors, accounts, maps, or social mechanics.

## Access and secrets

No credentials, tokens, or production secrets belong in this repository or this document. Request access through the project owner. Use a personal GitHub account with the least privilege needed; never share the owner’s account or personal access token.

The `yukabox` user can read the repository, but production-server SSH is not currently available from that user. Before assigning deployment work to a developer, provide their individual SSH public key and GitHub username, then grant only the repository role and server permissions they need.

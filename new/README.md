# new/ — the new-version preview (week 1)

A self-contained copy of the public site with the "week 1" presentation changes
applied. **Nothing outside `new/` is modified on this branch.** The live site
keeps running from `site/` + `server/` exactly as before; this copy is meant to
be served side-by-side at `new.joinmultiplayer.ai` so the two can be compared.

## What changed (week 1 of the UI plan)

1. **Trace pages fixed.** `/record/?id=T0001` used an undeclared
   `derivedQuestions` variable, so the render threw and the catch block showed
   "this trace does not exist" even though `/api/public/T0001` returned 200.
   The copy reads `record.derived_questions` / `record.continuations` safely.
2. **Persistent navigation.** A slim sticky nav under the goal ribbon:
   `i · Start here · Doors · Map · Experiments · Data` (EN/RU).
3. **"Start here" page** at `/start/` — the rules of the game on one screen:
   the three stories, one move, the dot (`ı → i`), the code legend
   (H/E/D/T/Q/V/M), what happens after a move, and a "give this page to your
   AI" block. Compressed from `GAME.md`.
4. **Home page.** "Enter" → "Try it in 2 minutes"; a plain-language
   lab subtitle under the hero; a three-step "how it works" strip
   (each step links to start/map/experiment); a "Start here" button.
5. **Morrow no longer covers buttons.** It collapses to a round face bubble
   (collapsed by default on the home page, expanded on guided flows); clicking
   the face toggles it. The old fully-hidden state migrates to "collapsed".
6. **Every empty state rewritten as an invitation** (EN + RU): traces,
   questions, map, data, physical runs, Codex runs, D08/D09 waiting doors —
   each now says what will appear, why it is interesting, and the smallest
   move to be first.

Supporting changes in the copy only:

- `PUBLIC_API_BASE` in `site/app.js`: when the copy is served from any host
  other than joinmultiplayer.ai, all **public GET** data (corpus, records,
  questions, events, map) is read from `https://joinmultiplayer.ai` (those
  endpoints are CORS-open), so the preview shows the real corpus. Form POSTs
  stay relative and land in this copy's own private moderation queue.
- `server/server.py` (copy): generic SPA fallback for extension-less routes
  (so `/start/`, `/d04`, `/map/` work behind any plain reverse proxy),
  `new.joinmultiplayer.ai` + `localhost:8092` added to allowed POST origins,
  default port 8092.
- `site/index.html` (copy): `noindex` (a preview must not compete with the
  real site in search), cache-buster `?v=new-week1`.
- A "NEW VERSION PREVIEW · current site →" banner renders only when the page
  is served from a non-production host; if this copy is ever promoted to the
  main domain, the banner disappears by itself.

## Run locally

```bash
python3 new/server/server.py --site new/site --db /tmp/new-preview.sqlite3 --port 8092
# open http://localhost:8092
```

## Deploy at new.joinmultiplayer.ai (yukabox)

1. Check out this branch next to the production checkout (do not touch the
   production one):
   `git clone -b claude/new-ui-week1 https://github.com/yukakust/joinmultiplayer.ai /srv/joinmultiplayer-new/checkout`
   then point the service at it, e.g.
   `app -> /srv/joinmultiplayer-new/checkout/new/server`,
   `public -> /srv/joinmultiplayer-new/checkout/new/site`.
2. Install the unit: copy `new/ops/joinmultiplayer-new-static.service` to
   `/etc/systemd/system/`, adjust paths, `systemctl enable --now` it.
   It listens on `127.0.0.1:8092` (production stays on 8091).
3. Add DNS `new.joinmultiplayer.ai` (same Cloudflare zone) and a reverse-proxy
   host that forwards `new.joinmultiplayer.ai` → `127.0.0.1:8092`, mirroring
   whatever fronts port 8091 today.
4. Compare, then delete the subdomain when done — production was never touched.

The preview's moderation queue is its own sqlite DB (`--db`); anything
submitted through the preview forms stays there and can be reviewed with
`new/server/moderate.py --db <that file>`.

## The town crier (the game calls, automatically)

`tools/crier.py` watches the public corpus and announces every new open
question that has no answers yet — "the game calls: the move is nobody's".
Without credentials it prints drafts (dry run). To make it post to
Telegram:

1. Create a bot via @BotFather, add it as admin to your channels/groups.
2. `echo 'TELEGRAM_BOT_TOKEN=...' > /etc/joinmultiplayer-crier.env` and add
   `TELEGRAM_CHAT_IDS=@your_channel,-100123456789`.
3. Install `ops/joinmultiplayer-crier.{service,timer}` and
   `systemctl enable --now joinmultiplayer-crier.timer`.

It never invents content — every post is verbatim from the corpus record.
Personalized invitations (AI drafting who to call and why, for you to send)
are the designed next step; see the doors' "For:" audiences as the target
map.

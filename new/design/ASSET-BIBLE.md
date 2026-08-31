# Promethean Forge — asset contract v0.1

The key screen is mood art. Production UI is assembled from individually approved assets.

## One object, one pass

- Never crop production assets from a composed scene.
- Generate or draw every figurine, relic, frame, and trail segment separately.
- Approve the silhouette before producing state variants.
- Keep the same camera, pedestal geometry, material family, and light direction across the set.

## Player pieces: the current production task

Player pieces are the people on the Trail. The fixed set is: match, matchbox,
lighter, flint, candle, lantern, lens, sparkler, plus an empty future slot.
Achievement statues and symbolic relics are a different, later task.

- Player-piece scale reference: `player-pieces/match/match-unlit-v2.png`.
- Universal pedestal master: `player-pieces/empty/empty-stand-v3.png`.
- Camera: front three-quarter, only slightly top-down.
- Silhouette: readable at 18 px; the carrier of fire occupies most of the height.
- Base: one standardized low blackened-bronze token base with one aged-brass rim.
  Every player piece uses the same pedestal diameter, height, tier profile, camera,
  and material scale; the carrier changes, the pedestal does not.
  The master is rendered on a 1149 × 1369 transparent canvas with a 930 px-wide
  pedestal footprint and a broad, flat top sized for the matchbox and lighter.
- Trail sockets are a separate, larger layer around that standardized pedestal.
  Never enlarge or shrink the player pedestal to fit a socket or a carrier.
- Light: upper-left studio key, restrained cool rim, ember light only in `lit`.
- Materials: broad intentional planes; sparse soot and patina; no random detail.
- Background: genuine transparent alpha, never a painted checkerboard.
- No labels, medallions, rewards, or additional symbolic meaning on a player piece.

## Required states

Each approved player piece has:

1. `unlit` — cold metal, no emissive light;
2. `lit` — exactly the same piece plus its prescribed flame layer.

Selection, hover, current-player, and disabled states belong to reusable UI overlays,
not redesigned sculptures.

## Current standardized set

- Match: `match-unlit-v2.png` / `match-lit-v2.png`
- Matchbox: `matchbox-unlit-v3.png` / `matchbox-lit-v5.png`
- Lighter: `lighter-unlit-v2.png` / `lighter-lit-v2.png`
- Candle: `candle-unlit-v2.png` / `candle-lit-v2.png`
- Flint: `flint-unlit-v2.png` / `flint-lit-v2.png`

All ten files use the same 1149 × 1369 canvas and the exact same
`empty-stand-v3.png` pedestal layer. Lit and unlit carrier placement is locked per
pair; state changes must never alter the silhouette or move the piece.

## Acceptance

- Exactly one object per source image.
- Clean alpha and edges, including flame glow.
- No illegible pseudo-text.
- No accidental extra fingers, floating pieces, or inconsistent ornaments.
- No direct imitation of an existing game asset.
- Compare at full size, 96 px, 48 px, and 18 px before approval.

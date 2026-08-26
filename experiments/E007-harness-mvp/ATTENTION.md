# E007 Checkpoint 3A — physical attention smoke

Status: completed and owner-published on 2026-08-26. All locked development
gates passed for one question and four manually authored cards.

## What we test

Only the first two agreed harness steps:

1. A person presses **Ask the pocket i network**. The harness keeps the exact
   text. It does not rewrite it or force it into JSON.
2. **Speculative Attention** sends a cheap beacon to four pocket i on two real
   devices. Each i compares the whole question with its public capability card
   and returns two visible scores.

No Qwen, private memory, RAG, training, answer generation, or secret data is
used in this smoke. A high score means "look here first", not "this i knows the
answer".

## Four physical processes

- `ATT-Y1` on yukabox — computer vision for small objects.
- `ATT-Y2` on yukabox — distributed systems and unreliable networks.
- `ATT-M1` on the owner's MacBook — computer-vision data diagnosis.
- `ATT-M2` on the owner's MacBook — beekeeping and hive observations.

These are four logical pocket i processes, not four trained neural models. Their
cards are written and approved by a human for this test. Automatic card creation
is a later, separate module.

## Visible scoring

Every process computes the same two deterministic signals locally:

- **whole-text vector** — cosine similarity between hashed character n-gram
  vectors for the exact question and the whole public card;
- **exact terms** — overlap of normalized words between the question and card.

This first vector is a transparent lexical baseline, not a learned semantic
embedding. It lets us test the network contract without silently downloading a
second neural model. A learned multilingual embedding model can replace this
module later without changing the relay or node contract.

Scores are raw ranking signals in `[0, 1]`. They are not probabilities and the
UI must not append `%`.

## Success for this smoke

- four unique processes answer from exactly two declared physical devices;
- every process reports the same SHA-256 hash of the unchanged question;
- every receipt exposes both scores, latency, card revision, and client version;
- the two computer-vision cards rank above both unrelated cards for the locked
  example question;
- no question or result becomes public until the owner explicitly publishes it.

Failure is also a result and stays in the public experiment history after owner
publication.

## Observed result

The exact Russian question reached four processes on two physical devices with
one identical SHA-256 hash. The whole-text vector ranked both CV cards above
both unrelated cards:

1. `ATT-Y1` small-object vision on yukabox — `0.224510`;
2. `ATT-M1` vision-data diagnosis on MacBook — `0.144365`;
3. `ATT-Y2` distributed systems on yukabox — `0.135640`;
4. `ATT-M2` beekeeping on MacBook — `0.125182`.

Both CV cards also found the exact term `cv`; the unrelated cards found no exact
term. This is a successful development smoke for delivery and ranking only. It
does not show semantic understanding and cannot yet tell whether a pocket i has
useful private knowledge. The frozen snapshot is
`site/experiments/E007/attention-result-v0.1.json`; the live public record is
`https://joinmultiplayer.ai/api/public/A0002`.

# Pocket i harness v0.2 — accepted path

Status: architecture checkpoint after E007 Gate 3C.6Q. Some blocks exist only
as tested parts. This is not yet a downloadable end-to-end product.

## The path

1. Install one modular Pocket i app and choose a model preset.
2. Keep the person's exact question and its hash.
3. Ask likely pocket i in parallel using public capability cards.
4. Each pocket i searches only memory its owner allowed.
5. Every contact ends as `found`, `empty`, `blocked`, `error`, or relay-created
   `offline`.
6. Before sending, a security module enforces permission and removes secrets.
7. Send a readable capsule: one claim, exact evidence, source location,
   lineage, conditions, limits, and permission.
8. Prefer recall at the sender: an uncertain useful piece may travel; losing it
   cannot be repaired later.
9. The receiver checks relevance with Qwen3-Reranker-4B Q4:
   `TAKE / NOT SURE / DROP`.
10. Ordinary code proves that the exact passage came from the named source
    snapshot and byte range.
11. DeBERTa NLI checks only `exact passage + one atomic claim`:
    `SUPPORTED / CONTRADICTED / NOT PROVEN`. The user question stays outside.
12. Keep each pocket i's knowledge as a chain: one current head plus preserved
    history. Check truth, applicability, and independence later, after all
    candidate answers arrive.
13. Merge only answers that make the same claim. Evidence, lineage, and a
    supported minority must remain visible.
14. A model writes the final answer only from accepted evidence and clearly
    names missing pieces.
15. The harness records `contacted → found → accepted → used → improved` so it
    learns value, not popularity.

## What Gate 3C.6P–Q taught us

The same NLI model scored `20/20` when it saw one exact source sentence and one
small claim. It scored `15/20` when we also mixed in the user's question and
surrounding document text. A human checked every gold label and all five new
errors.

So the accepted interface is deliberately narrow:

```text
exact verified source passage + one atomic claim
→ DeBERTa-v3-base NLI
→ SUPPORTED / CONTRADICTED / NOT PROVEN
```

This does not prove that the source is true, current, independent, applicable,
or safe to share. Those are different jobs for different modules.

## Evidence boundary

This is synthetic English development evidence reviewed by one researcher.
It still needs an independent held-out set, other languages, quantized-device
tests, and an end-to-end run on real pocket i devices.

## What Gate 12A taught us

The narrow chain mechanism is accepted. It found the current head and kept the
old records in 10/10 frozen synthetic cases. One three-record chain also moved
from yukabox to miracle-prod with the same SHA-256. This proves transport and
history mechanics only; it does not prove truth or applicability.

## What failed in Gate 13A

A frozen multilingual MiniLM embedding model tried to merge 21 English and
Russian answers. It recovered 0/6 paraphrase groups exactly, reached pairwise
F1 0.395062, and made 4/5 forbidden merges. It grouped answers about the same
topic even when they made different or opposing claims.

Therefore embeddings may find candidates, but they may not make the final
merge decision. This failed result is part of the public experiment history.

## What Gate 13B taught us

DeBERTa compared the 14 already opened English answers in both directions. Two
answers entered one pile only if each entailed the other. It recovered 4/6
paraphrase piles, made zero forbidden merges, lost no answers, and reached
pairwise F1 0.8. Two valid paraphrase pairs stayed separate.

This is safer than the embedding baseline, but it did not pass. DeBERTa also
called 19 unrelated pairs contradictions. Because this set had no separately
labelled true-conflict exam, the harness must not display those edges as real
disputes. Gate 13 remains open.

## What failed in Gate 13C

A second pass showed DeBERTa two complete piles and asked whether they express
the same claim. It recovered both missed pairs, but approved 42 false merges,
returned entailment for 44/45 pairs, and collapsed all answers into one group.

This checkpoint was trained for literal premise-to-hypothesis inference, not
meta-statements about groups. Do not add the Gate 13C second pass to the
accepted harness.

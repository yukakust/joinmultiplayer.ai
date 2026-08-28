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
12. Separate future modules must still check source truth, currentness,
    conditions, provenance, and independence.
13. Similar claims collapse, but their evidence and lineages remain visible.
    A supported minority is preserved.
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

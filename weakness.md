# Weaknesses of the current harness

This file records known weaknesses. We do not hide them and do not treat them as proof that the whole architecture is broken. Some are accepted for the MVP and can be fixed later.

## 1. Qwen sends related evidence too easily

Qwen can return a real quote even when that quote contradicts the claim instead of proving it.

- In Gate 16G.8 it did this for `2/10` unsupported English claims.
- This is currently acceptable only because the acceptance stage rejected both cases.
- A returned quote is a candidate, not accepted knowledge.

## 2. An exact quote may still be an incomplete proof

Qwen sometimes finds the correct rule but omits the fact that makes the rule apply now.

- In `EN01-G` it copied the Lyra-4 rule but omitted the message showing that the pressure-and-pulse condition occurred.
- In `EN08-G` it copied the Aster-9 rule and current temperature but omitted the message showing that cold-start frost occurred.
- It returned exact substrings for `10/10` supported claims, but manual review found complete evidence for only `8/10`.

The harness must never confuse these two checks:

1. Are these exact words present in the source?
2. Do these words contain every fact needed for the conclusion?

## 3. English DeBERTa rejects useful evidence

The current `DeBERTa-v3-base-mnli-fever-anli` is precise on this small test but has weak recall.

- It accepted `7/10` supported oracle evidence bundles.
- It accepted `0/10` unsupported oracle evidence bundles.
- It failed on multi-premise composition, numerical conditions, and negation involving words such as `only`.
- It must not be the only semantic judge.

## 4. Mechanical success can overstate real success

The automatic pipeline reported `7/10` supported claims accepted in Gate 16G.8. After checking whether Qwen had supplied the complete proof, only `5/10` were valid end to end.

Every important Gate therefore needs:

- frozen machine metrics;
- a separate human audit;
- a clear difference between exact text, complete evidence, and a correct conclusion.

## 5. The current MVP is English-only

All new harness tests use English for the question, claim, source, quote, instructions, and human label.

- Translation inside a test would mix translation errors with harness errors.
- Russian and mixed-language data are not supported by the validated MVP path yet.
- The mixed-language Gate 16G.7 is preserved as a diagnostic, not as an architecture decision.

## 6. Current evidence is still small and synthetic

Gate 16G.8 contains 20 fresh synthetic cases: 10 supported and 10 unsupported.

- The result is a development result, not production accuracy.
- The cases were locked before inference, but the final manual audit was not blind.
- A successful design still needs a fresh blind English replication and then real-device data.

## 7. Qwen3-8B is slow on the current CPU path

In Gate 16G.8 one short evidence decision took roughly 15–89 seconds on yukabox CPU.

- This is acceptable for research.
- It is not yet acceptable as an interactive product experience.
- We are prioritising answer quality before speed, but latency remains an open weakness.

## Current decision

We keep the present pipeline and move forward:

```text
find candidate chats
→ let Qwen find evidence
→ verify exact source spans with code
→ use DeBERTa as one cautious signal
→ preserve provenance and alternatives
→ do not present the result as certain truth
```

The current acceptance layer is conservative and incomplete. Its failures are recorded above so later modules can replace individual steps without rebuilding the whole harness.

## 8. A large first local index was invisible and all-or-nothing

The physical Mac Checkpoint 7C worker was still using CPU after 65 minutes, but
the app timed out after one hour and had not written a completed state. The
owner could see neither a message count nor remaining work and could not return
to chat. The run was stopped and rejected.

Checkpoint 7D saves every 128 new vectors, reports real saved-message counts,
has no fixed initial-build timeout, and keeps a `BACK TO CHAT` path. This is
covered by development tests; the physical rerun is still pending.

## 9. The first cited desktop answer is not yet fully evidence-checked

Checkpoint 7E produces one local answer instead of exposing raw search cards.
Code verifies that every displayed source label exists, but that does not prove
that every sentence follows from its excerpt. Exact quote extraction, DeBERTa,
shelves and owner approval before network transport are not wired into this
desktop path yet. The UI must not call the current answer verified.

## 10. Exact quotes are wired, but DeBERTa is not packaged yet

Checkpoint 7F rejects invented or altered quotes before the writer and rejects
final citations to unknown evidence. The accepted DeBERTa model is deliberately
not faked: without its frozen local files, the NLI interface returns
`unavailable`. The original safetensors alone are about 369 MB, and bundling a
full PyTorch runtime would make the desktop package much larger. The next gate
must export the exact accepted checkpoint to ONNX, compare its decisions with
the frozen reference cases, and only then add it to the app.

## Evidence

- Gate 16G.6 reader: `/experiment/e007/gate-16g/chat-first-reader/`
- Invalid mixed-language diagnostic: `/experiment/e007/gate-16g/quote-check/`
- English-only Gate 16G.8: `/experiment/e007/gate-16g/english-atomic-evidence/`

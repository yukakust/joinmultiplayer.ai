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

Checkpoint 7G completed that export. Dynamic INT8 was unusable (`9/30` matching
decisions), so the app keeps the much larger native FP16 ONNX file (`30/30`).
This preserves the tested decisions but adds about 378 MB before packaging
overhead and still needs a physical Mac load test.

## 11. A correct chat can still be cropped around the wrong word

The first physical alpha.9 question returned no supported information. The
excerpt function sorted question words mainly by length, so generic
`information` could win over the identifier `DeBERTa`. The router may therefore
find the right conversation while the reader receives the wrong 1,800-character
window. The next build prefers mixed-case names, digits, acronyms and IDs and
also returns a private count-only diagnostic code for the failed stage.

During owner-only alpha testing, alpha.11 additionally writes a complete local
`last-answer-test-log.json`: selected excerpts, raw Qwen extraction, exact-quote
decisions, DeBERTa signals, writer evidence and final output. It is mode `0600`,
contains private text, is never uploaded, and must be removed from release builds.

The trace proved the first alpha.11 failure was not caused by cropping: the
right passage reached Qwen and Qwen understood it, but altered the quote while
copying it. Alpha.12 therefore numbers immutable evidence blocks and lets Qwen
select IDs only. Unit tests prove exact reconstruction and rejection of unknown
IDs; usefulness and physical behavior still require the repeated Mac question.

The repeated alpha.12 question exposed the next artificial restriction: Qwen
correctly selected three blocks covering both halves of the question, but the
harness rejected them because they came from `S1` and `S7`. Alpha.13 permits a
single conclusion to preserve up to four exact blocks across sources. This is
necessary for composition, but also makes DeBERTa's multi-block judgment a new
physical checkpoint rather than a proven capability.

## 12. DeBERTa went from ignored to an over-strict quote-only gate

The alpha.13 ten-question physical regression scored 3 correct, 2 partial and
5 wrong (`8/20`). Both deliberately absent answers were invented. In the fully
traced final case, retrieval found an adjacent DoRA/Cerebras passage, Qwen
answered an absent named-model question from it, and DeBERTa returned `neutral`
with `0.996094` confidence. The harness still handed the claim to the writer.
Therefore the current NLI field is metadata, not an acceptance turnstile, and
the build is not safe for an external tester.

Alpha.14 fixed the ignored-warning bug: `neutral`, `contradiction`, and
`unavailable` stopped before the writer. The owner's physical regression then
exposed the other half of the known problem. The desktop supplied only short
selected blocks, so supported claims were rejected by the same quote-only
failure mode measured in Gate 16D.9. This is why several real answers became
`I couldn't find supported information` while the absent E099 answer was
correctly blocked.

Alpha.15 candidate restores the accepted input contract: immutable exact quote
plus bounded neighbouring text from the same source, checked against one atomic
claim. Gate 16D.11 is encouraging development evidence, not a substitute for a
new physical regression. Until that run passes, false-negative grounding
remains an open weakness.

Alpha.15 also retained only the last private audit, so a ten-question run erased
the first nine diagnostic traces. Alpha.16 keeps an append-only local file per
question while retaining the last-log convenience copy. Existing overwritten
logs cannot be reconstructed; the four false-negative questions must be run
again.

The first preserved alpha.17 trace shows a separate retrieval failure. The
question about `/x` reached Qwen with ten unrelated excerpts and stopped at
`no_candidates_extracted`; DeBERTa was never called. The current word tokenizer
reduces `/x` to `x`, whole chats are ranked by their single best message, and
only two messages per selected chat are exposed. Checkpoint 7P therefore tests
an exact-anchor-aware route in a private A/B before changing the application.

## 13. Grounded does not mean relevant to the question

Checkpoint 7R tested one additive conversation chosen from automatically rare
two- and three-word query phrases. In 30 physical questions it was selected by
Qwen three times, recovered no final answer, and caused one irrelevant answer
to pass. DeBERTa correctly rejected one other irrelevant claim, but also
rejected one claim backed by the exact passage needed for the question. The
current NLI step asks whether source context entails a claim; it does not prove
that the claim answers the owner's question. Phrase fallback is therefore not
accepted, despite improving retrieval-only recall from 3/4 to 4/4.

## Evidence

- Gate 16G.6 reader: `/experiment/e007/gate-16g/chat-first-reader/`
- Invalid mixed-language diagnostic: `/experiment/e007/gate-16g/quote-check/`
- English-only Gate 16G.8: `/experiment/e007/gate-16g/english-atomic-evidence/`

## 14. Top-five conversation retrieval can omit the answer

In the owner ten-question cutoff run, Q05 and Q06 reached the reranker with five
unrelated conversations. The expected evidence was absent, so lowering the
reranker cutoff could not recover either answer. This is an upstream retrieval
false negative, not a grounding or writer failure.

Open work with Vitaly: test `question → correct conversation` on answered and
answerless questions, then improve recall without turning superficially similar
technical text into evidence.

## 15. One oversized candidate can abort all candidates

Q07 and Q08 stopped before relevance decisions because individual reranker
inputs contained 32,792 and 10,084 tokens while the live server used an 8,192
token physical batch. The HTTP 500 from one candidate aborted the complete
question. Q08 already contained a short source with the correct free-tier
explanation, but that useful source was lost with the failed batch.

Open work with Vitaly: isolate failure per candidate. Continue processing
normal candidates and send the oversized item to the explicit long-message
path. Do not silently crop whole messages and do not treat infrastructure
failure as semantic `DROP`.

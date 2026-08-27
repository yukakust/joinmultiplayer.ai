# Gate 3C.5 raw scores

- `bf16-scores.json` — pinned Hugging Face BF16 source model on yukabox CPU.
- `q4_k_m-scores.json` — self-built GGUF Q4_K_M candidate.
- `q5_k_m-scores.json` — self-built GGUF Q5_K_M candidate.
- `gguf-bf16-scores.json` — technical equivalence check for the GGUF rank
  endpoint; it is not a fourth scientific condition.
- `bf16-runtime.txt` — `/usr/bin/time -v` output for the source run.

The GGUF server uses rank pooling over the exact frozen Gate 3C.5 prompt. The
BF16 GGUF technical check differed from Transformers by a mean absolute
probability of 0.001293 and a maximum of 0.014071 across the 40 calibration and
exam pairs.

The model files are intentionally not committed. Their exact source and
llama.cpp revisions, quantization names, gates, and size limit are recorded in
`site/experiments/E007/mobile-reranker-protocol-v0.1.json`; measured file sizes
and all decisions are in
`site/experiments/E007/mobile-reranker-result-v0.1.json`.

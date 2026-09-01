"""Compare a prepared ONNX NLI artifact with frozen public decisions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer


LABELS = ("entailment", "neutral", "contradiction")
FROZEN_RESULTS = (
    "nli-deberta-result-v0.1.json",
    "nli-fresh20-short-result-v0.1.json",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True)
    args = parser.parse_args()
    records = []
    for filename in FROZEN_RESULTS:
        payload = json.loads((args.repo / "site/experiments/E007" / filename).read_text())
        records.extend(payload["records"])
    tokenizer = Tokenizer.from_file(str(args.model_dir / "tokenizer.json"))
    tokenizer.enable_truncation(max_length=512)
    tokenizer.enable_padding()
    encodings = tokenizer.encode_batch([(item["premise"], item["hypothesis"]) for item in records])
    session = ort.InferenceSession(str(args.model_dir / "model.onnx"), providers=["CPUExecutionProvider"])
    logits = session.run(None, {
        "input_ids": np.asarray([item.ids for item in encodings], dtype=np.int64),
        "attention_mask": np.asarray([item.attention_mask for item in encodings], dtype=np.int64),
    })[0]
    decisions = [LABELS[int(index)] for index in logits.argmax(axis=1)]
    mismatches = [item["id"] for item, decision in zip(records, decisions) if decision != item["decision"]]
    print(json.dumps({"matches": len(records) - len(mismatches), "total": len(records), "mismatches": mismatches}))
    return 0 if not mismatches else 1


if __name__ == "__main__":
    raise SystemExit(main())

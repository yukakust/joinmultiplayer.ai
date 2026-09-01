"""Local English NLI signal backed by the frozen validated ONNX model."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence


LABELS = ("entailment", "neutral", "contradiction")


class LocalNli:
    def __init__(self, model_dir: Path) -> None:
        model_path = model_dir / "model.onnx"
        tokenizer_path = model_dir / "tokenizer.json"
        if not model_path.is_file() or not tokenizer_path.is_file():
            raise FileNotFoundError("local NLI files are missing")
        import onnxruntime as ort
        from tokenizers import Tokenizer

        options = ort.SessionOptions()
        options.log_severity_level = 3
        self.session = ort.InferenceSession(
            str(model_path), sess_options=options, providers=["CPUExecutionProvider"]
        )
        self.tokenizer = Tokenizer.from_file(str(tokenizer_path))
        self.tokenizer.enable_truncation(max_length=512)
        self.tokenizer.enable_padding()

    def __call__(self, pairs: Sequence[tuple[str, str]]) -> Sequence[tuple[str, float]]:
        import numpy as np

        if not pairs:
            return ()
        encodings = self.tokenizer.encode_batch(list(pairs))
        feed = {
            "input_ids": np.asarray([item.ids for item in encodings], dtype=np.int64),
            "attention_mask": np.asarray([item.attention_mask for item in encodings], dtype=np.int64),
        }
        logits = self.session.run(None, feed)[0]
        logits = logits - logits.max(axis=1, keepdims=True)
        probabilities = np.exp(logits)
        probabilities /= probabilities.sum(axis=1, keepdims=True)
        decisions = probabilities.argmax(axis=1)
        return tuple(
            (LABELS[int(index)], float(probabilities[row, index]))
            for row, index in enumerate(decisions)
        )

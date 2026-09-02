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
        self.window_tokenizer = Tokenizer.from_file(str(tokenizer_path))
        self.tokenizer.enable_truncation(max_length=512)
        self.tokenizer.enable_padding()

    def centered_source_premise(
        self,
        contexts: Sequence[tuple[str, Sequence[str]]],
        claim: str,
        maximum_tokens: int = 512,
    ) -> str:
        """Fit source-only neighbour context while keeping every exact quote."""
        clean = []
        for source, quotes in contexts:
            unique = tuple(dict.fromkeys(item for item in quotes if item))
            if not source or not unique or any(item not in source for item in unique):
                raise ValueError("exact quote missing from source context")
            clean.append((source, unique))
        if not clean:
            raise ValueError("source context is required")

        claim_tokens = len(self.window_tokenizer.encode(claim, add_special_tokens=False).ids)
        # DeBERTa pairs add CLS + two SEP tokens. Reserve one extra token for
        # separators inserted between multiple source windows.
        premise_budget = maximum_tokens - claim_tokens - 4
        exact_sizes = [
            len(self.window_tokenizer.encode(" ".join(quotes), add_special_tokens=False).ids)
            for _source, quotes in clean
        ]
        separator_budget = max(0, len(clean) - 1)
        if premise_budget < sum(exact_sizes) + separator_budget:
            raise ValueError("exact evidence and claim do not fit the NLI context")
        remaining = premise_budget - sum(exact_sizes) - separator_budget

        windows = []
        for index, ((source, quotes), exact_size) in enumerate(zip(clean, exact_sizes)):
            share = remaining // len(clean) + (1 if index < remaining % len(clean) else 0)
            budget = exact_size + share
            encoding = self.window_tokenizer.encode(source, add_special_tokens=False)
            quote_ranges = []
            search_start = 0
            for quote in quotes:
                start = source.find(quote, search_start)
                if start < 0:
                    start = source.find(quote)
                end = start + len(quote)
                quote_ranges.append((start, end))
                search_start = end
            quote_tokens = [
                token_index
                for token_index, (start, end) in enumerate(encoding.offsets)
                if any(end > quote_start and start < quote_end for quote_start, quote_end in quote_ranges)
            ]
            if not quote_tokens:
                raise ValueError("exact evidence has no NLI tokens")
            first_quote, last_quote = min(quote_tokens), max(quote_tokens)
            if last_quote - first_quote + 1 > budget:
                window = " ".join(quotes)
            else:
                spare = budget - (last_quote - first_quote + 1)
                start_token = max(0, first_quote - spare // 2)
                end_token = min(len(encoding.ids), start_token + budget)
                start_token = max(0, end_token - budget)
                window = source[encoding.offsets[start_token][0] : encoding.offsets[end_token - 1][1]]
            if any(quote not in window for quote in quotes):
                raise RuntimeError("bounded source window lost exact evidence")
            windows.append(window)

        premise = "\n".join(windows)
        if len(self.window_tokenizer.encode(premise, claim).ids) > maximum_tokens:
            raise RuntimeError("bounded NLI pair exceeded its token budget")
        return premise

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

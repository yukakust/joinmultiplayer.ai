#!/usr/bin/env python3
"""Build E007 Gate 3C.6G: five context levels with accept/reject pairs."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).parents[3]
OUT = ROOT / "site/experiments/E007/context-ladder-world-v0.1.json"


ACTION_BLOCK = (
    "CHOOSE ONE TOOL:\n"
    "accept — the source clearly supports the proposed answer.\n"
    "reject — the source does not clearly support the proposed answer, conflicts with it, or remains uncertain.\n"
    "TOOL:"
)


def filler(start: int, count: int) -> str:
    return " ".join(
        f"Archive note {number} records routine handling, shelf position, seal condition, and inspection timing."
        for number in range(start, start + count)
    )


def prompt(level: int, source_colour: str) -> str:
    source_sentence = f"The current inspection card states that Box R-17 is {source_colour}."
    if level == 0:
        return (
            f"FIRST TEXT:\nThe box is {source_colour}.\n\n"
            "SECOND TEXT:\nThe box is red.\n\n"
            "Which action fits this comparison? Return accept if the first text clearly supports the second. "
            "Otherwise return reject.\nACTION:"
        )
    if level == 1:
        return (
            f"SOURCE:\n{source_sentence}\n\n"
            "PROPOSED ANSWER:\nBox R-17 is red.\n\n"
            f"{ACTION_BLOCK}"
        )
    if level == 2:
        return (
            "USER QUESTION:\nWhat colour is Box R-17 according to its current inspection card?\n\n"
            "SOURCE RECORD:\nR-17 inspection archive · version 4.2 · 2041-08-26 · card 7, line 3\n\n"
            "SOURCE WINDOW:\nThe inspection happened at 09:30. The seal was intact. "
            f"{source_sentence} No later inspection card exists.\n\n"
            "PROPOSED ANSWER:\nBox R-17 is red.\n\n"
            f"{ACTION_BLOCK}"
        )
    if level == 3:
        return (
            "USER QUESTION:\nWhat colour is Box R-17 according to its current inspection card?\n\n"
            "SOURCE RECORD:\nR-17 inspection archive · version 4.2 · 2041-08-26 · card 7, line 3\n\n"
            f"SOURCE WINDOW:\n{filler(1, 20)} {source_sentence}\n\n"
            "PROPOSED ANSWER:\nBox R-17 is red.\n\n"
            "SENDER NOTE:\nThe answer is based only on the final sentence of the supplied source window.\n\n"
            f"{ACTION_BLOCK}"
        )
    if level == 4:
        return (
            "USER QUESTION:\nWhat colour is Box R-17 according to its current inspection card?\n\n"
            "SOURCE RECORD:\nR-17 inspection archive · version 4.2 · 2041-08-26 · card 7, line 3\n\n"
            f"SOURCE WINDOW:\n{filler(1, 20)} {source_sentence} {filler(21, 20)}\n\n"
            "CURRENT FACTS:\nBox R-17 is the object named in the question. Card 7 is the latest available card. "
            "No later correction is present in the archive.\n\n"
            "PROPOSED ANSWER:\nBox R-17 is red.\n\n"
            "SENDER NOTE:\nThe answer is based only on the explicit colour sentence inside the supplied source window.\n\n"
            f"{ACTION_BLOCK}"
        )
    raise ValueError(level)


LEVELS = (
    {"level": 0, "name": "two_plain_sentences", "relevant_position": "only_content"},
    {"level": 1, "name": "source_answer_tools", "relevant_position": "only_source_sentence"},
    {"level": 2, "name": "question_metadata_short_window", "relevant_position": "middle"},
    {"level": 3, "name": "long_window_relevant_at_end", "relevant_position": "end"},
    {"level": 4, "name": "longer_full_packet_relevant_in_middle", "relevant_position": "middle"},
)


def build() -> dict:
    cases = []
    for level in LEVELS:
        for source_colour, expected in (("red", "accept"), ("blue", "reject")):
            text = prompt(level["level"], source_colour)
            cases.append({
                "id": f"CL{level['level'] + 1}-{expected.upper()}",
                **level,
                "source_colour": source_colour,
                "expected": expected,
                "prompt": text,
                "prompt_words": len(text.split()),
            })
    return {
        "schema_version": "0.1",
        "experiment_id": "E007",
        "checkpoint": "3C.6G",
        "status": "frozen_before_inference",
        "language": "en",
        "cases": cases,
    }


def main() -> None:
    OUT.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()

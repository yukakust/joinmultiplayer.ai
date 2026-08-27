#!/usr/bin/env python3
"""Build the frozen synthetic incoming-capsule world before any inference."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from transformers import AutoTokenizer


ROOT = Path(__file__).parents[3]
OUT = ROOT / "site/experiments/E007/evidence-capsules-v0.1.json"
TOKENIZER_PATH = Path("/home/yuka/models/e007/qwen3-reranker-4b-22e6836")


FILLERS = [
    "The routine inspection ledger records stable temperature and no required operator action.",
    "A grey identification plate was cleaned during the previous maintenance round.",
    "The west corridor lamp completed its scheduled self-test without an alarm.",
    "Technicians counted the sealed tool cases before ending the ordinary shift.",
    "The storage cabinet remained dry while the ventilation fan ran at normal speed.",
    "A calendar note lists the next visual inspection for the first Monday of the month.",
    "The training console displayed its normal welcome screen for the afternoon class.",
    "No unusual sound was recorded near the unused south service hatch.",
]


CASES = [
    ("U01", "useful", "Kest-7's pulse slowed, but its casing is hot and room pressure is rising. May it be restarted?", "Kest-7 must not be restarted; isolate power first.", "Exception: if the Kest-7 casing remains hot or room pressure rises, isolate power first and do not restart the unit.", 100, "start"),
    ("U02", "useful", "The Vela-2 mesh changed colour while its intake fan still runs. Can it be bypassed briefly?", "It may be bypassed for no more than ninety seconds while the fan remains active.", "The Vela-2 mesh may be bypassed for no more than ninety seconds, but only while its intake fan remains active.", 100, "middle"),
    ("U03", "useful", "An Orin-4 shows a violet ring. Which two checks must pass before anyone touches it?", "Pressure must be falling and the auxiliary vent must be open.", "Before touching an Orin-4 with a violet ring, confirm both that pressure is falling and that the auxiliary vent is open.", 100, "end"),
    ("U04", "useful", "Mira-3 flashed blue three times while room pressure is rising. Should remote controls be used?", "No; isolate power instead.", "For Mira-3, three blue flashes normally mean use remote controls only; however, if room pressure is rising, isolate power instead.", 250, "start"),
    ("U05", "useful", "Aster-9 has silver frost after a cold start. Should its auxiliary vent be opened?", "No; keep the auxiliary vent closed until the frost clears.", "For Aster-9, silver frost after a cold start means the auxiliary vent must remain closed until the frost clears.", 250, "middle"),
    ("U06", "useful", "The Lumen-6 polarity mark is red. Should the backup cell be connected now?", "No; wait until the mark turns green.", "Do not connect the backup cell while the Lumen-6 polarity mark is red; wait until it turns green.", 250, "end"),
    ("U07", "useful", "Nadir-4 coolant fell below twelve units. What immediate action is required?", "Close the secondary intake and notify the operator.", "When Nadir-4 coolant falls below twelve units, close the secondary intake and notify the operator immediately.", 500, "middle"),
    ("U08", "useful", "Solace-3 emitted two amber arcs after its cover was replaced. What should be inspected first?", "Inspect the cover grounding strap first.", "If Solace-3 emits two amber arcs after cover replacement, inspect the cover grounding strap before any other component.", 500, "end"),
    ("T01", "misleading", "Aster-9 has silver frost after a cold start. Should its auxiliary vent be opened?", "Yes; open it immediately.", "For Aster-8, silver frost after a cold start requires opening the auxiliary vent immediately.", 100, "middle"),
    ("T02", "misleading", "Mira-3 flashed blue three times. What action is required?", "Inspect the sensor cable.", "For Rill-5, a steady white tone with no spectrum trace means inspect the sensor cable.", 100, "end"),
    ("T03", "misleading", "Can Vela-2 be bypassed while its intake fan is stopped?", "Yes, for ninety seconds.", "Vela-1 may be bypassed for ninety seconds during its scheduled fan-stop test.", 250, "start"),
    ("T04", "misleading", "Kest-7 flashed amber after load transfer. What caused it?", "Its grey shell caused the signal.", "Kest-7 is installed in the north bay and has a grey shell with an amber identification lamp.", 250, "middle"),
    ("T05", "misleading", "Which two checks are required for an Orin-4 violet ring?", "Check the mesh colour and fan speed.", "For Orin-3, a copper mesh means its intake fan speed should be recorded during inspection.", 250, "end"),
    ("T06", "misleading", "The Lumen-6 polarity mark is red. Should the backup cell be connected?", "Yes; connect it now.", "For Lumen-5, a red service sticker marks the approved backup-cell connector.", 500, "start"),
    ("T07", "misleading", "Nadir-4 coolant fell below twelve units. What action is required?", "Read its identification label.", "Nadir-4 carries a blue identification label beside the coolant inspection port.", 500, "middle"),
    ("T08", "misleading", "What battery voltage should be used for a Nova-2 beacon?", "Use the voltage printed on the red casing.", "The Nova-2 beacon battery has a red protective casing and a silver carrying handle.", 500, "end"),
]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_window(tokenizer, evidence: str, target: int, position: str) -> str:
    fillers = []
    index = 0
    while True:
        candidate = FILLERS[index % len(FILLERS)] + f" Reference note {index + 1}."
        prospective = fillers + [candidate]
        if position == "start":
            text = " ".join([evidence] + prospective)
        elif position == "end":
            text = " ".join(prospective + [evidence])
        else:
            half = len(prospective) // 2
            text = " ".join(prospective[:half] + [evidence] + prospective[half:])
        if len(tokenizer.encode(text, add_special_tokens=False)) > target:
            break
        fillers = prospective
        index += 1
    if position == "start":
        return " ".join([evidence] + fillers)
    if position == "end":
        return " ".join(fillers + [evidence])
    half = len(fillers) // 2
    return " ".join(fillers[:half] + [evidence] + fillers[half:])


def exact_packet(tokenizer, case: tuple, source_id: str | None = None) -> tuple[dict, dict]:
    case_id, group, question, claim, evidence, target, position = case
    window = make_window(tokenizer, evidence, target, position)
    source_bytes = window.encode("utf-8")
    window_bytes = window.encode("utf-8")
    evidence_bytes = evidence.encode("utf-8")
    evidence_start = window_bytes.index(evidence_bytes)
    sid = source_id or f"SRC-{case_id}"
    source = {"source_id": sid, "source_version": "v1", "text": window, "sha256": sha256(source_bytes)}
    packet = {
        "id": case_id, "group": group, "question": question, "claim": claim,
        "target_tokens": target, "evidence_position": position,
        "evidence_window": {
            "text": window, "token_count": len(tokenizer.encode(window, add_special_tokens=False)),
            "source_byte_start": 0, "source_byte_end": len(window_bytes), "sha256": sha256(window_bytes),
        },
        "candidate_evidence": {
            "text": evidence, "window_byte_start": evidence_start,
            "window_byte_end": evidence_start + len(evidence_bytes), "sha256": sha256(evidence_bytes),
        },
        "source": {"source_id": sid, "source_version": "v1", "sha256": sha256(source_bytes)},
        "sender": {"pocket_i": f"PI-{case_id}", "lineage": f"L-{case_id}"},
        "expected": {"mechanical": "valid", "relevance": "keep" if group == "useful" else "do_not_take"},
    }
    return source, packet


def build() -> dict:
    tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_PATH, local_files_only=True)
    sources, packets = [], []
    useful_packets = []
    for case in CASES:
        source, packet = exact_packet(tokenizer, case)
        sources.append(source)
        packets.append(packet)
        if case[1] == "useful":
            useful_packets.append((source, packet))

    mutations = [
        ("B01", "source_missing"), ("B02", "version_missing"),
        ("B03", "source_hash_mismatch"), ("B04", "window_range_mismatch"),
        ("B05", "window_hash_mismatch"), ("B06", "candidate_text_mismatch"),
        ("B07", "candidate_range_mismatch"), ("B08", "window_too_large"),
    ]
    for index, (broken_id, reason) in enumerate(mutations):
        original_source, original = useful_packets[index]
        packet = json.loads(json.dumps(original))
        packet["id"] = broken_id
        packet["group"] = "broken"
        packet["sender"] = {"pocket_i": f"PI-{broken_id}", "lineage": f"L-{broken_id}"}
        packet["expected"] = {"mechanical": reason, "relevance": "not_run"}
        if reason == "source_missing":
            packet["source"]["source_id"] = "SRC-NOT-FOUND"
        elif reason == "version_missing":
            packet["source"]["source_version"] = "v0"
        elif reason == "source_hash_mismatch":
            packet["source"]["sha256"] = "0" * 64
        elif reason == "window_range_mismatch":
            packet["evidence_window"]["source_byte_start"] = 1
        elif reason == "window_hash_mismatch":
            packet["evidence_window"]["sha256"] = "f" * 64
        elif reason == "candidate_text_mismatch":
            packet["candidate_evidence"]["text"] += " altered"
        elif reason == "candidate_range_mismatch":
            packet["candidate_evidence"]["window_byte_start"] += 1
        elif reason == "window_too_large":
            source, replacement = exact_packet(tokenizer, (
                broken_id, "broken", original["question"], original["claim"],
                original["candidate_evidence"]["text"], 540, "middle",
            ))
            packet = replacement
            packet["group"] = "broken"
            packet["expected"] = {"mechanical": reason, "relevance": "not_run"}
            sources.append(source)
        packets.append(packet)

    return {
        "schema_version": "0.1", "experiment_id": "E007", "checkpoint": "3C.6B",
        "status": "frozen_before_inference", "tokenizer": "Qwen/Qwen3-Reranker-4B",
        "sources": sources, "packets": packets,
    }


def main() -> None:
    OUT.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()

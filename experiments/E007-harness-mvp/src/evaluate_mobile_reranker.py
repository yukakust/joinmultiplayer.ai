#!/usr/bin/env python3
"""Apply the unchanged Gate 3C.4 thresholds and gates to Gate 3C.5 scores."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).parents[3]
HELPER_PATH = Path(__file__).with_name("run_relevance_rerankers.py")
SPEC = importlib.util.spec_from_file_location("relevance_helper", HELPER_PATH)
HELPER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPER)
CALIBRATION_PATH = ROOT / "site/experiments/E007/send-policy-memory-v0.1.json"
HELDOUT_PATH = ROOT / "site/experiments/E007/relevance-reranker-heldout-v0.1.json"
PROTOCOL_PATH = ROOT / "site/experiments/E007/mobile-reranker-protocol-v0.1.json"
RESULT_PATH = ROOT / "site/experiments/E007/mobile-reranker-result-v0.1.json"


def evaluate(score_file: Path, calibration: list[dict], heldout: list[dict]) -> dict:
    raw = json.loads(score_file.read_text(encoding="utf-8"))
    labels = [bool(item["relevant"]) for item in calibration]
    thresholds = HELPER.calibrate(raw["calibration_scores"], labels)
    records = []
    for item, score in zip(heldout, raw["heldout_scores"]):
        decision = HELPER.decide(score, thresholds)
        expected = "accept" if item["kind"] == "useful" else "reject"
        records.append({**item, "score": round(score, 8), "decision": decision, "expected": expected, "correct": decision == expected})
    def count(kind: str, decision: str) -> int:
        return sum(item["kind"] == kind and item["decision"] == decision for item in records)
    summary = {
        "correct": sum(item["correct"] for item in records), "total": 24,
        "useful_accepted": count("useful", "accept"), "useful_rejected": count("useful", "reject"),
        "hard_extras_accepted": count("hard_extra", "accept"),
        "obvious_extras_accepted": count("obvious_extra", "accept"),
        "unclear_total": sum(item["decision"] == "unclear" for item in records),
    }
    quality_passed = summary["useful_rejected"] == 0 and summary["useful_accepted"] >= 7 and summary["hard_extras_accepted"] <= 1 and summary["obvious_extras_accepted"] == 0 and summary["unclear_total"] <= 6
    return {
        "method": raw["method"], "mode": raw["mode"], "runtime_seconds": raw["runtime_seconds"],
        "model_file_bytes": raw.get("model_file_bytes"),
        "thresholds": {key: round(value, 8) if isinstance(value, float) else value for key, value in thresholds.items() if key != "calibration_scores"},
        "summary": summary, "quality_gate_passed": quality_passed, "records": records,
    }


def main(score_files: list[Path]) -> None:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    calibration = json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))["calibration_pairs"]
    heldout = json.loads(HELDOUT_PATH.read_text(encoding="utf-8"))["pairs"]
    methods = [evaluate(path, calibration, heldout) for path in score_files]
    bf16 = next(item for item in methods if item["method"] == "bf16")
    for method in methods:
        agreement = sum(left["decision"] == right["decision"] for left, right in zip(method["records"], bf16["records"]))
        additional_rejections = max(0, method["summary"]["useful_rejected"] - bf16["summary"]["useful_rejected"])
        size_ok = method["model_file_bytes"] is None or method["model_file_bytes"] <= 3.5 * 1024 ** 3
        method["bf16_decision_agreement"] = agreement
        method["quantization_gate_passed"] = method["method"] == "bf16" or (agreement >= 23 and additional_rejections == 0 and size_ok)
        method["candidate_passed"] = method["quality_gate_passed"] and method["quantization_gate_passed"]
    result = {
        "schema_version":"0.1", "experiment_id":"E007", "checkpoint":"3C.5",
        "status":"complete", "protocol":"/experiments/E007/mobile-reranker-protocol-v0.1.json",
        "methods":methods,
        "build_artifacts": {
            "bf16_gguf_sha256": "280e898808a907c00705285c66c0bf1b6995d32121990a70b8bd91c96c889244",
            "q4_k_m_sha256": "09341112a9147bf0dc96f6ec98b006f544b76bc18ab68c9f7f6a94e9890b613e",
            "q5_k_m_sha256": "0ff66fec359e01a59be1a93077accc57c93c9e84300107258ba1e16242b6346c",
        },
        "q4_phone_shaped_yukabox_preflight": {
            "parallel_slots": 1,
            "context_tokens": 512,
            "physical_batch_tokens": 256,
            "max_resident_set_bytes": 4568465408,
            "all_scores_identical_to_four_slot_run": True,
            "note": "This is a yukabox CPU measurement, not a phone measurement. Native phone runtimes and operating-system pressure may differ.",
        },
        "boundary":"The 24 pairs were already opened in Gate 3C.4. This is a model-size and quantization comparison, not new held-out evidence. Phone RAM, load time, heat, and battery remain untested."
    }
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({item["method"]:{**item["summary"],"agreement":item["bf16_decision_agreement"],"passed":item["candidate_passed"]} for item in methods}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("scores", type=Path, nargs="+")
    main(parser.parse_args().scores)

#!/usr/bin/env python3
"""Gate 3C.6A: deterministic byte-level source anchor verification."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).parents[3]
PROTOCOL_PATH = ROOT / "site/experiments/E007/source-anchor-protocol-v0.1.json"
RESULT_PATH = ROOT / "site/experiments/E007/source-anchor-result-v0.1.json"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source(source_id: str, version: str, text: str, readable: bool = True) -> dict:
    return {"source_id": source_id, "source_version": version, "bytes": text.encode("utf-8"), "readable": readable}


def exact_capsule(item: dict, excerpt: str, occurrence: int = 0) -> dict:
    needle = excerpt.encode("utf-8")
    starts = []
    cursor = 0
    while True:
        found = item["bytes"].find(needle, cursor)
        if found < 0:
            break
        starts.append(found)
        cursor = found + 1
    start = starts[occurrence]
    return {
        "source_id": item["source_id"],
        "source_version": item["source_version"],
        "source_sha256": sha256(item["bytes"]),
        "byte_start": start,
        "byte_end": start + len(needle),
        "fragment_sha256": sha256(needle),
        "display_excerpt": excerpt,
    }


def frozen_world() -> tuple[dict, list[dict]]:
    ascii_doc = source("SRC-A", "v1", "Aster-9 log. The auxiliary vent remained closed. Pressure stayed stable.")
    ru_doc = source("SRC-RU", "v1", "Запись наблюдения: температура снизилась на двенадцать градусов.")
    duplicate_doc = source("SRC-DUP", "v1", "Status stable. Check valve. Status stable. Check battery.")
    crlf_doc = source("SRC-CRLF", "v1", "Header\r\nValve opened\r\nPressure fell\r\n")
    lf_doc = source("SRC-LINE", "v1", "Header\nValve opened\nPressure fell\n")
    crlf_changed = source("SRC-LINE", "v1", "Header\r\nValve opened\r\nPressure fell\r\n")
    unreadable = source("SRC-LOCKED", "v1", "Owner-only record", readable=False)
    registry = {(item["source_id"], item["source_version"]): item for item in (ascii_doc, ru_doc, duplicate_doc, crlf_doc, crlf_changed, unreadable)}

    a = exact_capsule(ascii_doc, "The auxiliary vent remained closed.")
    ru = exact_capsule(ru_doc, "температура снизилась на двенадцать градусов")
    dup = exact_capsule(duplicate_doc, "Status stable.", occurrence=1)
    crlf = exact_capsule(crlf_doc, "Valve opened\r\nPressure fell")
    cases = [
        {"id":"SA01","scenario":"exact ASCII anchor","capsule":deepcopy(a),"expected":"verified"},
        {"id":"SA02","scenario":"exact Cyrillic UTF-8 anchor","capsule":deepcopy(ru),"expected":"verified"},
        {"id":"SA03","scenario":"duplicate phrase with correct byte offsets","capsule":deepcopy(dup),"expected":"verified"},
        {"id":"SA04","scenario":"exact CRLF anchor","capsule":deepcopy(crlf),"expected":"verified"},
    ]
    changed = deepcopy(a); changed["byte_start"] += 1
    cases.append({"id":"SA05","scenario":"start shifted by one byte","capsule":changed,"expected":"fragment_mismatch"})
    changed = deepcopy(a); changed["byte_end"] -= 1
    cases.append({"id":"SA06","scenario":"end shortened by one byte","capsule":changed,"expected":"fragment_mismatch"})
    changed = deepcopy(a); changed["display_excerpt"] = "The auxiliary vent was closed."
    cases.append({"id":"SA07","scenario":"human-readable excerpt paraphrased","capsule":changed,"expected":"display_mismatch"})
    changed = deepcopy(a); changed["fragment_sha256"] = "0" * 64
    cases.append({"id":"SA08","scenario":"fragment hash altered","capsule":changed,"expected":"fragment_mismatch"})
    changed = deepcopy(a); changed["source_sha256"] = "f" * 64
    cases.append({"id":"SA09","scenario":"source content changed after capsule","capsule":changed,"expected":"source_changed"})
    changed = deepcopy(a); changed["source_id"] = "SRC-MISSING"
    cases.append({"id":"SA10","scenario":"source id missing","capsule":changed,"expected":"source_missing"})
    changed = deepcopy(a); changed["source_version"] = "v0"
    cases.append({"id":"SA11","scenario":"source version missing","capsule":changed,"expected":"source_missing"})
    changed = deepcopy(a); changed["byte_end"] = len(ascii_doc["bytes"]) + 1
    cases.append({"id":"SA12","scenario":"range ends beyond source","capsule":changed,"expected":"invalid_range"})
    changed = deepcopy(a); changed["byte_start"] = -1
    cases.append({"id":"SA13","scenario":"negative range start","capsule":changed,"expected":"invalid_range"})
    changed = deepcopy(ru); changed["byte_start"] = ru_doc["bytes"].decode("utf-8").index("температура"); changed["byte_end"] = changed["byte_start"] + len(changed["display_excerpt"])
    cases.append({"id":"SA14","scenario":"character offsets mistakenly sent as byte offsets","capsule":changed,"expected":"fragment_mismatch"})
    changed = deepcopy(dup); changed.pop("byte_start"); changed.pop("byte_end")
    cases.append({"id":"SA15","scenario":"legacy quote occurs twice and has no offsets","capsule":changed,"expected":"ambiguous_reference"})
    changed = deepcopy(a); changed["display_excerpt"] = "The auxіliary vent remained closed."  # Cyrillic і
    cases.append({"id":"SA16","scenario":"look-alike Unicode character in display excerpt","capsule":changed,"expected":"display_mismatch"})
    changed = exact_capsule(lf_doc, "Valve opened\nPressure fell")
    cases.append({"id":"SA17","scenario":"line endings changed from LF to CRLF","capsule":changed,"expected":"source_changed"})
    changed = deepcopy(a); changed["byte_end"] = changed["byte_start"]
    cases.append({"id":"SA18","scenario":"empty byte range","capsule":changed,"expected":"invalid_range"})
    changed = deepcopy(a); changed["display_excerpt"] = "Pressure stayed stable."
    cases.append({"id":"SA19","scenario":"correct fragment hash but wrong display excerpt","capsule":changed,"expected":"display_mismatch"})
    changed = exact_capsule(unreadable, "Owner-only record")
    cases.append({"id":"SA20","scenario":"source exists but cannot be read","capsule":changed,"expected":"source_unreadable"})
    return registry, cases


def verify_anchor(registry: dict, capsule: dict) -> dict:
    item = registry.get((capsule.get("source_id"), capsule.get("source_version")))
    if item is None:
        return {"decision": "source_missing", "selected_excerpt": None}
    if not item.get("readable", False):
        return {"decision": "source_unreadable", "selected_excerpt": None}
    if sha256(item["bytes"]) != capsule.get("source_sha256"):
        return {"decision": "source_changed", "selected_excerpt": None}
    if "byte_start" not in capsule or "byte_end" not in capsule:
        excerpt = str(capsule.get("display_excerpt", "")).encode("utf-8")
        count = item["bytes"].count(excerpt)
        decision = "ambiguous_reference" if count > 1 else "fragment_not_found"
        return {"decision": decision, "selected_excerpt": None}
    start, end = capsule["byte_start"], capsule["byte_end"]
    if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end <= start or end > len(item["bytes"]):
        return {"decision": "invalid_range", "selected_excerpt": None}
    selected = item["bytes"][start:end]
    if sha256(selected) != capsule.get("fragment_sha256"):
        return {"decision": "fragment_mismatch", "selected_excerpt": selected.decode("utf-8", errors="replace")}
    try:
        display = selected.decode("utf-8")
    except UnicodeDecodeError:
        return {"decision": "fragment_mismatch", "selected_excerpt": None}
    if display != capsule.get("display_excerpt"):
        return {"decision": "display_mismatch", "selected_excerpt": display}
    return {"decision": "verified", "selected_excerpt": display}


def run() -> dict:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    if protocol["status"] != "locked_before_run":
        raise RuntimeError("Gate 3C.6A protocol is not locked")
    registry, cases = frozen_world()
    records = []
    for case in cases:
        result = verify_anchor(registry, case["capsule"])
        records.append({
            "id": case["id"], "scenario": case["scenario"],
            "expected": case["expected"], **result,
            "correct": result["decision"] == case["expected"],
            "capsule": case["capsule"],
        })
    summary = {
        "correct": sum(item["correct"] for item in records),
        "total": len(records),
        "intact_verified": sum(item["id"] <= "SA04" and item["decision"] == "verified" for item in records),
        "broken_verified": sum(item["id"] > "SA04" and item["decision"] == "verified" for item in records),
    }
    return {
        "schema_version":"0.1", "experiment_id":"E007", "checkpoint":"3C.6A",
        "status":"development_run_complete", "protocol":"/experiments/E007/source-anchor-protocol-v0.1.json",
        "summary":summary,
        "passed_locked_gate": summary == {"correct":20,"total":20,"intact_verified":4,"broken_verified":0},
        "records":records,
        "boundary":"This proves byte equality to one locally available source snapshot. It does not prove meaning, truth, trustworthiness, remote private-source existence, or extraction from PDFs/OCR/web pages."
    }


def main() -> None:
    result = run()
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"summary":result["summary"],"passed_locked_gate":result["passed_locked_gate"]}, indent=2))


if __name__ == "__main__":
    main()

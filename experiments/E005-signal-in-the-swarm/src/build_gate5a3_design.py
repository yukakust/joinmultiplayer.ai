from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
EXAM = ROOT / "site/experiments/E005/gate-5a2-locked-test-v0.1.json"
OUT = ROOT / "site/experiments/E005/gate-5a3-design-v0.1.json"


def content_hash(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def build() -> dict:
    exam = json.loads(EXAM.read_text(encoding="utf-8"))
    design = {
        "experiment_id": "E005",
        "gate": "5A.3",
        "kind": "locked_semantic_capsule_synthesis_design",
        "status": "locked_not_run",
        "reuses_exam_content_sha256": exam["content_sha256"],
        "question": {
            "en": "Can a final i preserve two pocket i when their capsules contain meaningful statements instead of secret codes?",
            "ru": "Сможет ли финальный i сохранить знания двух pocket i, если в капсулах будут понятные утверждения, а не тайные коды?",
        },
        "fixed": [
            "the same 24 Gate 5A.2 questions",
            "the same trained CAUSE-I and SAFETY-I adapters",
            "greedy generation without internet or RAG",
            "one round: both pockets answer in parallel, then one source model answers",
        ],
        "changed": [
            "a deterministic codebook expands each actual pocket label into a human-readable claim",
            "the capsule names the observed signal and its pocket as provenance",
            "the answer budget grows from 64 to 192 tokens",
            "frozen Qwen3-0.6B-Base is compared with frozen Qwen3-0.6B post-trained for instructions",
        ],
        "semantic_capsule_contract": {
            "cause": {
                "claim": "CAUSE-I concludes that the cause is thermal rebound.",
                "basis": "CAUSE-I matched the observed device signal using its personal diagnostic skill.",
                "source": "CAUSE-I",
            },
            "safety": {
                "action": "Keep the auxiliary vent closed.",
                "basis": "SAFETY-I matched the observed work-zone signal using its personal safety skill.",
                "source": "SAFETY-I",
            },
        },
        "conditions": [
            "base_question_alone",
            "base_semantic_actual_pair",
            "instruct_question_alone",
            "instruct_semantic_actual_pair",
            "instruct_cause_only",
            "instruct_safety_only",
            "instruct_semantic_oracle_pair",
        ],
        "pass_rule": {
            "instruct_actual_complete_at_least": 20,
            "instruct_actual_natural_at_least": 20,
            "instruct_question_alone_complete_at_most": 8,
            "instruct_each_missing_capsule_complete_at_most": 8,
            "instruct_oracle_complete_at_least": 20,
            "no_output_may_be_scored_after_token_cutoff": True,
        },
        "plain_limit": {
            "en": "This tests a text protocol between pocket i. It is not the planned neural network with parallel hidden-state tracks.",
            "ru": "Это тест текстового протокола между pocket i. Это ещё не запланированная нейросеть с параллельными скрытыми треками.",
        },
        "training_performed": False,
        "run_performed": False,
    }
    design["content_sha256"] = content_hash(design)
    return design


def main() -> None:
    OUT.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

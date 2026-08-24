from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
ARTIFACTS = ROOT / "experiments/E005-signal-in-the-swarm/artifacts"
OUTPUT = ROOT / "site/experiments/E005/gate-4c-training-v0.1.json"
RUNS = {
    "source_work": ARTIFACTS / "gate4c-source-correct-v0.1/summary.json",
    "safe_action": ARTIFACTS / "gate4c-safe-correct-v0.1/summary.json",
}


def build() -> dict:
    summaries = {skill: json.loads(path.read_text(encoding="utf-8")) for skill, path in RUNS.items()}
    runs = []
    for skill, summary in summaries.items():
        runs.append({key: summary[key] for key in (
            "skill", "control", "seed", "model_id", "model_revision", "curriculum_content_sha256",
            "examples", "epochs", "steps", "max_length", "rank", "alpha", "learning_rate",
            "target_modules", "use_dora", "trainable_parameters", "total_parameters", "loss_first",
            "loss_last", "loss_mean_first_24", "loss_mean_last_24", "elapsed_seconds",
            "base_hash_before", "base_hash_after", "base_unchanged", "adapter_sha256",
        )})
    payload = {
        "experiment_id": "E005",
        "gate": "4C",
        "version": "training-v0.1",
        "kind": "public_synthetic_development_training_checkpoint",
        "status": "two_personal_adapters_trained_exam_not_run",
        "runner_git_revision": "8798ebf",
        "runs": runs,
        "checks": {
            "all_runs_used_same_frozen_base": len({run["base_hash_before"] for run in runs}) == 1,
            "base_unchanged_after_every_run": all(run["base_unchanged"] for run in runs),
            "exam_was_read_by_training_runner": False,
            "rag_used": False,
        },
        "plain_language": {
            "en": "Two new pocket i changed only their small personal DoRA weights. Their training error fell. This proves the training pipe worked, not that either skill transfers to new questions.",
            "ru": "Два новых pocket i изменили только свои маленькие личные DoRA-веса. Ошибка на уроках снизилась. Это доказывает работу обучения, но ещё не перенос умения на новые вопросы.",
        },
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    payload["content_sha256"] = hashlib.sha256(canonical).hexdigest()
    return payload


def main() -> None:
    OUTPUT.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

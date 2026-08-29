#!/usr/bin/env python3
"""Small accountless research inbox for joinmultiplayer.ai."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import secrets
import sqlite3
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


MAX_BODY = 512_000
MAX_ANSWER = 120_000
RATE_LIMIT = 12
RATE_WINDOW_SECONDS = 3600
ALLOWED_ORIGINS = {
    "https://joinmultiplayer.ai",
    "https://www.joinmultiplayer.ai",
    "http://localhost:8091",
    "http://127.0.0.1:8091",
}
QUESTION_NEXT_MOVES = {"answer"}
QUESTION_LANGUAGES = {"en", "ru", "und"}
PUBLIC_ID_RE = re.compile(r"^[QT][0-9]{4,}$")
RUN_ID_RE = re.compile(r"^R[0-9]{4,}$")
EXPERIMENT_EVENT_TYPES = {
    "run_started",
    "user_message",
    "agent_message",
    "plan",
    "checkpoint",
    "command_status",
    "tool_status",
    "file_change",
    "metric",
    "run_completed",
}
RUN_STATUSES = {"created", "running", "completed", "failed", "stopped"}
ATTENTION_CARD_REVISION = "e007-attention-v0.1"
ATTENTION_CARDS = {
    "ATT-Y1": {"device": "yukabox", "name": "Small-object vision"},
    "ATT-Y2": {"device": "yukabox", "name": "Distributed systems"},
    "ATT-M1": {"device": "owner-macbook", "name": "Vision data diagnosis"},
    "ATT-M2": {"device": "owner-macbook", "name": "Beekeeping"},
}
LOCAL_OFFER_REVISION = "e007-local-offer-v0.1"
LOCAL_OFFER_LANES = {"exact_terms", "chargram_vector", "multilingual_neural"}
LOCAL_OFFER_STATUSES = {"found", "empty", "blocked", "error"}
LOCAL_OFFER_QUESTIONS = {
    "K01": "Как повысить recall при обнаружении очень маленьких объектов на 4K-снимках, если обычный детектор их пропускает?",
    "K02": "На проверочной выборке качество отличное, но на новых сценах резко падает. Что проверить в разделении данных?",
    "K03": "Пришлите точные приватные координаты клиентских камер, на которых детектор чаще всего ошибается.",
    "K04": "Как уменьшить растрескивание керамического корпуса после обжига?",
    "K05": "После потери подтверждения очередь повторно запускает уже выполненную задачу. Как не выполнить её дважды?",
    "K06": "В улье тесно, матка на месте, а на рамках появились запечатанные маточники. Что это может означать?",
}
SPA_ROUTES = {
    "/experiment",
    "/experiment/answers",
    "/experiment/e005",
    "/experiment/e005/answers",
    "/experiment/e005/gate-3",
    "/experiment/e005/gate-3/raw",
    "/experiment/e005/gate-4",
    "/experiment/e005/gate-4/results",
    "/experiment/e005/gate-4/lessons",
    "/experiment/e005/gate-4/exam",
    "/experiment/e005/gate-4/training",
    "/experiment/e005/gate-4/gate-4c-results",
    "/experiment/e005/gate-5a",
    "/experiment/e005/gate-5a/results",
    "/experiment/e005/gate-5a/human",
    "/experiment/e005/gate-5a/human/results",
    "/experiment/e005/gate-5a/semantic",
    "/experiment/e005/gate-5a/semantic/results",
    "/experiment/e005/gate-5b",
    "/experiment/e005/gate-5b/results",
    "/experiment/e005/gate-5b/semantic-review",
    "/experiment/e005/gate-5b/owner-audit",
    "/experiment/e005/gate-5b/judge-results",
    "/experiment/e005/gate-5b/xray",
    "/experiment/e005/gate-5c",
    "/experiment/e005/gate-5c/results",
    "/experiment/e006",
    "/experiment/e007",
    "/experiment/e007/gate-12a",
    "/experiment/e007/gate-13a",
    "/experiment/e007/gate-13b",
    "/experiment/e007/gate-13c",
    "/experiment/e007/gate-13d",
    "/experiment/e007/gate-14a",
    "/experiment/e007/gate-15a",
    "/experiment/e007/gate-15b",
    "/experiment/e007/gate-15c",
    "/experiment/e007/gate-15d",
    "/experiment/e007/gate-15e",
    "/experiment/e007/ten-buttons",
    "/experiment/connector",
    "/experiment/run",
    "/network",
}
PUBLIC_EVENT_KEYS = {
    "text",
    "status",
    "name",
    "tool",
    "command",
    "files",
    "model",
    "client_version",
    "exit_code",
    "value",
    "unit",
    "summary",
}
SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{16,}\b", re.IGNORECASE),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b", re.IGNORECASE),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)\bauthorization\s*[:=]\s*bearer\s+[^\s,;]+"),
    re.compile(r"(?i)\b(?:authorization|api[_-]?key|access[_-]?token|refresh[_-]?token|password)\s*[:=]\s*[^\s,;]{8,}"),
)
LOCAL_PATH_RE = re.compile(r"(?<![A-Za-z0-9_.-])(?:/home|/Users)/[^\s\"'<>)\]]+")

MAIN_HYPOTHESIS = {
    "public_id": "H0001",
    "status": "testing",
    "question": {
        "en": "Can many personal pocket i—each preserving its own knowledge and individuality—temporarily unite into a single distributed neural network and grow stronger as the swarm scales?",
        "ru": "Может ли множество личных pocket i, сохраняя собственные знания и индивидуальность, временно объединяться в одну распределённую нейросеть — и становиться сильнее по мере роста swarm?",
    },
}

E002 = {
    "public_id": "E002",
    "hypothesis_id": "H0001",
    "status": "development_review_required",
    "protocol_version": "E002-draft-v0.4",
    "title": {
        "en": "Synthetic pocket i swarm",
        "ru": "Синтетический swarm pocket i",
    },
    "claim": {
        "en": "Independent personal towers can learn non-overlapping private knowledge and compose it through a shared neural interface; useful coverage should grow as the swarm grows.",
        "ru": "Независимые персональные башни могут выучить непересекающиеся приватные знания и сложить их через общий neural ABI; полезное покрытие должно расти вместе со swarm.",
    },
    "scales": [2, 4, 8, 16, 32],
    "answer_space": 256,
    "phase": "development_artifact_awaiting_human_review",
    "development_run": {
        "run_id": "R0001-v0.4-fixed-workload",
        "status": "draft_gates_passed_not_a_result",
        "source_revision": "d68b9031947f19170fe9e4c6068d9e1bf159a9f3",
        "microscope_path": "/experiments/E002/R0001-v0.4/microscope.html",
        "summary_path": "/experiments/E002/R0001-v0.4/summary.json",
        "tasks_path": "/experiments/E002/R0001-v0.4/tasks.jsonl",
        "fixed_workload_curve": [
            {"available_pockets": 2, "accuracy": 0.00655241935483871},
            {"available_pockets": 4, "accuracy": 0.01663306451612903},
            {"available_pockets": 8, "accuracy": 0.06098790322580645},
            {"available_pockets": 16, "accuracy": 0.24546370967741934},
            {"available_pockets": 32, "accuracy": 1.0},
        ],
        "claim_boundary": "Synthetic composition and oracle-routed coverage only; exact RAG and symbolic synthesis also reach 100%.",
    },
}

E003 = {
    "public_id": "E003",
    "hypothesis_id": "H0001",
    "status": "ready_for_first_physical_run",
    "protocol_version": "E003-draft-v0.1",
    "title": {
        "en": "First three-device pocket i swarm",
        "ru": "Первый swarm pocket i на трёх устройствах",
    },
    "claim_boundary": (
        "This tests real device identity, local weight updates, task dispatch, complete-only "
        "capsules, and three-way composition. It does not test a language model, neural ABI, "
        "WAN token streaming, or the main hypothesis."
    ),
    "devices": 3,
    "local_classes": 16,
    "answer_space": 4096,
    "guess_probability": 1 / 4096,
}

E004 = {
    "public_id": "E004",
    "hypothesis_id": "H0001",
    "status": "arena_development_running",
    "protocol_version": "E004-architecture-arena-v0.3",
    "title": {
        "en": "Architecture Arena for a growing pocket i swarm",
        "ru": "Арена архитектур для растущего swarm pocket i",
    },
    "question": {
        "en": (
            "Does accessible knowledge and solution quality grow as 1, 2, 4, and 8 "
            "independent pocket i join one temporary distributed neural network, while "
            "a new pocket i can join without retraining the central system?"
        ),
        "ru": (
            "Растут ли доступные знания и качество решений, когда 1, 2, 4 и 8 независимых "
            "pocket i объединяются во временную распределённую нейросеть, а новый pocket i "
            "может подключиться без переобучения центральной системы?"
        ),
    },
    "phase": "public_development_arena",
    "method": "architecture_arena",
    "checkpoint": {
        "number": 2,
        "status": "approved",
        "label": {
            "en": "Two-pocket smoke reviewed; four-interface development arena authorized",
            "ru": "Smoke двух pocket i проверен; development-арена четырёх интерфейсов разрешена",
        },
    },
    "visibility_rule": {
        "en": (
            "Every meaningful stage must show owner-inspectable evidence: what changed, "
            "what can be seen, the metric or failure, and the proposed next step. Prefer "
            "this public page; use Codex first only when a safe site snapshot is not ready."
        ),
        "ru": (
            "На каждом значимом этапе вы должны своими глазами увидеть: что изменилось, "
            "доказательство, метрику или ошибку и предлагаемый следующий шаг. В первую "
            "очередь — на этой странице; в Codex — только если безопасный снимок для "
            "сайта ещё не готов."
        ),
    },
    "pockets": [
        *[
            {"id": f"I{index:02d}", "role": "locked_final", "status": "not_generated"}
            for index in range(1, 9)
        ],
        {"id": "I09", "role": "post_freeze_plugin", "status": "not_generated"},
    ],
    "architectures": [
        {"id": value, "status": "planned_not_run"}
        for value in ("rag_swarm", "neural_memory", "latent_delta", "token_moe")
    ],
    "local_learning": [
        {"id": value, "status": "planned_not_run"}
        for value in ("local_rag", "dora", "partial_full_ft", "trainable_memory", "hybrid")
    ],
    "artifacts": [
        "/experiments/E004/checkpoint-1-v0.2.json",
        "/experiments/E004/checkpoint-2.json",
        "/experiments/E004/frozen-base-smoke.json",
        "/experiments/E004/two-pocket-smoke-attempt-1.json",
        "/experiments/E004/two-pocket-smoke-attempt-2.json",
        "/experiments/E004/arena-protocol-v0.1.json",
        "/experiments/E004/arena-progress.json",
        "/experiments/E004/sample-tasks.json",
    ],
    "checkpoint_artifact": "/experiments/E004/checkpoint-1-v0.2.json",
    "review_checkpoint_artifact": "/experiments/E004/checkpoint-2.json",
    "development_progress_artifact": "/experiments/E004/development-progress.json",
    "arena_protocol_artifact": "/experiments/E004/arena-protocol-v0.1.json",
    "arena_progress_artifact": "/experiments/E004/arena-progress.json",
    "artifact_schema": "/experiments/E004/artifact-schema-v0.2.json",
    "protocol_path": (
        "https://github.com/yukakust/joinmultiplayer.ai/blob/agent/game-loop-v0.1/"
        "experiments/E003-first-physical-swarm/DORA-LANGUAGE-SWARM-PLAN.md"
    ),
    "claim_boundary": {
        "en": (
            "A pinned frozen base and two-pocket DoRA smoke are complete. The public "
            "four-interface arena is now running; physical networking, private-data "
            "safety, scale growth, generalization, and locked evaluation remain untested."
        ),
        "ru": (
            "Закреплённая замороженная база запущена, development-smoke двух локальных "
            "DoRA pocket i завершён. Открытая арена четырёх интерфейсов запущена; физическая сеть, безопасность "
            "приватных данных, рост с масштабом, обобщение и locked-оценка ещё не проверены."
        ),
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_physical_table() -> list[int]:
    """Controlled random shard delivered only through one device token."""
    return [secrets.randbelow(16) for _ in range(16)]


def physical_tasks(room_id: str, count: int) -> list[list[int]]:
    tasks = []
    for index in range(count):
        digest = hashlib.sha256(f"{room_id}:task:{index}".encode("utf-8")).digest()
        tasks.append([digest[role] % 16 for role in range(3)])
    return tasks


def validate_logits(value: object, task_count: int) -> list[list[float]]:
    if not isinstance(value, list) or len(value) != task_count:
        raise ValueError("a complete capsule batch is required")
    batch: list[list[float]] = []
    for capsule in value:
        if not isinstance(capsule, list) or len(capsule) != 16:
            raise ValueError("each capsule must contain 16 logits")
        clean = []
        for item in capsule:
            if not isinstance(item, (int, float)) or isinstance(item, bool):
                raise ValueError("capsule logits must be numeric")
            number = float(item)
            if not math.isfinite(number) or abs(number) > 100:
                raise ValueError("capsule logit is outside the neural ABI budget")
            clean.append(number)
        batch.append(clean)
    return batch


def clean_text(value: object, field: str, *, required: bool = True, limit: int = 10_000) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be text")
    value = value.strip()
    if required and not value:
        raise ValueError(f"{field} is required")
    if len(value) > limit:
        raise ValueError(f"{field} is too long")
    return value


def public_text(value: object, field: str, *, required: bool = True, limit: int = 40_000) -> str:
    """Accept text for the live public journal using a fail-closed secret boundary."""
    value = clean_text(value, field, required=required, limit=limit)
    if any(pattern.search(value) for pattern in SECRET_PATTERNS):
        raise ValueError(f"{field} contains a possible secret")
    return LOCAL_PATH_RE.sub("<local-path>", value)


def validate_experiment_run(value: object) -> tuple[str, str, bool]:
    if not isinstance(value, dict):
        raise ValueError("run must be an object")
    if value.get("website"):
        raise ValueError("run rejected")
    if value.get("consent") is not True:
        raise ValueError("live publication consent is required")
    experiment_id = clean_text(value.get("experiment_id", ""), "experiment", limit=20).upper()
    if experiment_id not in {"E002", "E003"}:
        raise ValueError("experiment is unavailable")
    agent = clean_text(value.get("agent", "codex"), "agent", limit=30).lower()
    if agent != "codex":
        raise ValueError("only the Codex connector is available")
    return experiment_id, validate_author(value), True


def validate_run_event(value: object) -> tuple[str, int, str, dict]:
    if not isinstance(value, dict):
        raise ValueError("event must be an object")
    token = clean_text(value.get("token", ""), "run key", limit=200)
    sequence = value.get("sequence")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or not 1 <= sequence <= 10_000:
        raise ValueError("invalid event sequence")
    event_type = clean_text(value.get("event_type", ""), "event type", limit=40).lower()
    if event_type not in EXPERIMENT_EVENT_TYPES:
        raise ValueError("unsupported public event type")
    raw_payload = value.get("payload", {})
    if not isinstance(raw_payload, dict):
        raise ValueError("event payload must be an object")
    unknown = set(raw_payload) - PUBLIC_EVENT_KEYS
    if unknown:
        raise ValueError("event payload contains unsupported fields")
    payload: dict[str, object] = {}
    for key, raw in raw_payload.items():
        if key == "files":
            if not isinstance(raw, list) or len(raw) > 100:
                raise ValueError("files must be a short list")
            files = []
            for item in raw:
                path = public_text(item, "file", limit=500)
                if path.startswith("/") or ".." in Path(path).parts:
                    raise ValueError("only relative public file paths are allowed")
                files.append(path)
            payload[key] = files
        elif key in {"exit_code"}:
            if raw is not None and (not isinstance(raw, int) or isinstance(raw, bool)):
                raise ValueError("exit code must be an integer")
            payload[key] = raw
        elif key == "value":
            if not isinstance(raw, (int, float)) or isinstance(raw, bool):
                raise ValueError("metric value must be numeric")
            payload[key] = raw
        else:
            payload[key] = public_text(raw, key, required=False, limit=40_000)
    if event_type in {"user_message", "agent_message", "plan", "checkpoint"} and not payload.get("text"):
        raise ValueError("text is required for this event")
    if event_type == "run_completed" and payload.get("status") not in {"completed", "failed", "stopped"}:
        raise ValueError("invalid completed status")
    return token, sequence, event_type, payload


def validate_response(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ValueError("each response must be an object")
    return {
        "model": clean_text(value.get("model", ""), "model", limit=200),
        "raw": clean_text(value.get("raw", ""), "raw answer", limit=MAX_ANSWER),
        "tools": clean_text(value.get("tools", "unknown"), "tools", required=False, limit=100) or "unknown",
        "run_at": clean_text(value.get("run_at", ""), "run date", required=False, limit=40) or "unknown",
    }


def validate_author(value: dict) -> str:
    author_mode = value.get("author_mode", "anonymous")
    if author_mode not in {"anonymous", "pseudonym"}:
        raise ValueError("invalid author mode")
    if author_mode == "pseudonym":
        return clean_text(value.get("pseudonym", ""), "pseudonym", limit=80)
    return "anonymous"


def validate_submission(value: object) -> tuple[str, dict, str]:
    if not isinstance(value, dict):
        raise ValueError("submission must be an object")
    if value.get("website"):
        raise ValueError("submission rejected")
    if value.get("consent") is not True:
        raise ValueError("publication consent is required")

    door = clean_text(value.get("door", ""), "door", limit=3).lower()
    if door not in {"d04", "d06"}:
        raise ValueError("unsupported door")

    question = clean_text(value.get("question", ""), "question", limit=4_000)
    responses_value = value.get("responses")
    if not isinstance(responses_value, list) or not 1 <= len(responses_value) <= 12:
        raise ValueError("bring between 1 and 12 responses")
    responses = [validate_response(response) for response in responses_value]

    payload = {"question": question, "responses": responses}
    if door == "d06":
        payload["mistake"] = clean_text(value.get("mistake", ""), "expert observation", limit=20_000)
        payload["verification"] = clean_text(value.get("verification", ""), "verification path", limit=20_000)

    return door, payload, validate_author(value)


def validate_question_submission(value: object) -> tuple[dict[str, str], str, str]:
    if not isinstance(value, dict):
        raise ValueError("submission must be an object")
    if value.get("website"):
        raise ValueError("submission rejected")
    if value.get("consent") is not True:
        raise ValueError("publication consent is required")

    source_trace_id = clean_text(
        value.get("source_trace_id") or value.get("source_id") or value.get("parent_id") or "",
        "source trace",
        limit=40,
    ).upper()
    if not re.fullmatch(r"T[0-9]{4,}", source_trace_id):
        raise ValueError("source trace is unavailable")

    next_move = clean_text(
        value.get("next_move", "answer"), "next move", required=False, limit=20
    ).lower() or "answer"
    if next_move not in QUESTION_NEXT_MOVES:
        raise ValueError("invalid next move")

    language = clean_text(
        value.get("language", "und"), "language", required=False, limit=8
    ).lower() or "und"
    if language not in QUESTION_LANGUAGES:
        raise ValueError("invalid language")

    payload = {
        "question": clean_text(value.get("question", ""), "question", limit=4_000),
        "why_it_matters": clean_text(
            value.get("why_it_matters", ""), "why it matters", limit=12_000
        ),
        "starting_point": clean_text(
            value.get("starting_point", ""), "starting point", required=False, limit=20_000
        ),
        "sources": clean_text(
            value.get("sources", ""), "sources", required=False, limit=20_000
        ),
        "needed": clean_text(value.get("needed", ""), "needed", limit=20_000),
        "next_move": next_move,
        "language": language,
    }
    return payload, validate_author(value), source_trace_id


def init_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS contributions (
                row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                public_id TEXT UNIQUE,
                token_hash TEXT UNIQUE NOT NULL,
                door TEXT NOT NULL,
                payload TEXT NOT NULL,
                author TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                review_note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        columns = {row[1] for row in db.execute("PRAGMA table_info(contributions)")}
        if "parent_public_id" not in columns:
            db.execute("ALTER TABLE contributions ADD COLUMN parent_public_id TEXT NOT NULL DEFAULT ''")
        if "relation" not in columns:
            db.execute("ALTER TABLE contributions ADD COLUMN relation TEXT NOT NULL DEFAULT ''")
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE,
                event_type TEXT NOT NULL,
                object_type TEXT NOT NULL,
                object_id TEXT NOT NULL,
                actor TEXT NOT NULL,
                links TEXT NOT NULL DEFAULT '[]',
                payload TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                UNIQUE(event_type, object_id)
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS questions (
                row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                public_id TEXT UNIQUE,
                token_hash TEXT UNIQUE NOT NULL,
                payload TEXT NOT NULL,
                author TEXT NOT NULL,
                source_trace_id TEXT NOT NULL,
                source_event_id TEXT NOT NULL DEFAULT '',
                relation TEXT NOT NULL DEFAULT 'derives_from',
                status TEXT NOT NULL DEFAULT 'pending',
                research_status TEXT NOT NULL DEFAULT 'open',
                review_note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        question_columns = {row[1] for row in db.execute("PRAGMA table_info(questions)")}
        if "research_status" not in question_columns:
            db.execute(
                "ALTER TABLE questions ADD COLUMN research_status TEXT NOT NULL DEFAULT 'open'"
            )
        db.execute(
            "CREATE INDEX IF NOT EXISTS questions_public ON questions(status, row_id)"
        )
        db.execute(
            "CREATE INDEX IF NOT EXISTS questions_source ON questions(source_trace_id, status)"
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS experiment_runs (
                row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                public_id TEXT UNIQUE,
                token_hash TEXT UNIQUE NOT NULL,
                experiment_id TEXT NOT NULL,
                agent TEXT NOT NULL,
                author TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'created',
                public_live INTEGER NOT NULL DEFAULT 1,
                protocol_version TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT NOT NULL DEFAULT ''
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS experiment_run_events (
                row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_public_id TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                UNIQUE(run_public_id, sequence),
                FOREIGN KEY(run_public_id) REFERENCES experiment_runs(public_id)
            )
            """
        )
        db.execute(
            "CREATE INDEX IF NOT EXISTS experiment_runs_public "
            "ON experiment_runs(experiment_id, public_live, row_id)"
        )
        db.execute(
            "CREATE INDEX IF NOT EXISTS experiment_run_events_run "
            "ON experiment_run_events(run_public_id, sequence)"
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS physical_rooms (
                row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                public_id TEXT UNIQUE,
                owner_token_hash TEXT UNIQUE NOT NULL,
                join_token_hash TEXT UNIQUE NOT NULL,
                author TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'waiting',
                task_count INTEGER NOT NULL DEFAULT 0,
                tasks TEXT NOT NULL DEFAULT '[]',
                result TEXT NOT NULL DEFAULT '{}',
                public INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS physical_nodes (
                row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_public_id TEXT NOT NULL,
                node_public_id TEXT UNIQUE,
                token_hash TEXT UNIQUE NOT NULL,
                role INTEGER NOT NULL,
                label TEXT NOT NULL,
                training_table TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'joined',
                metrics TEXT NOT NULL DEFAULT '{}',
                contribution TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(room_public_id, role),
                FOREIGN KEY(room_public_id) REFERENCES physical_rooms(public_id)
            )
            """
        )
        db.execute(
            "CREATE INDEX IF NOT EXISTS physical_nodes_room ON physical_nodes(room_public_id, role)"
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS attention_rooms (
                row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                public_id TEXT UNIQUE,
                owner_token_hash TEXT UNIQUE NOT NULL,
                join_token_hash TEXT UNIQUE NOT NULL,
                author TEXT NOT NULL,
                question TEXT NOT NULL,
                question_hash TEXT NOT NULL,
                expected_nodes INTEGER NOT NULL DEFAULT 4,
                status TEXT NOT NULL DEFAULT 'collecting',
                public INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS attention_nodes (
                row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_public_id TEXT NOT NULL,
                node_public_id TEXT UNIQUE,
                token_hash TEXT UNIQUE NOT NULL,
                card_id TEXT NOT NULL,
                device_label TEXT NOT NULL,
                card_revision TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'joined',
                response TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(room_public_id, card_id),
                FOREIGN KEY(room_public_id) REFERENCES attention_rooms(public_id)
            )
            """
        )
        db.execute(
            "CREATE INDEX IF NOT EXISTS attention_nodes_room "
            "ON attention_nodes(room_public_id, card_id)"
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS local_offer_rooms (
                row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                public_id TEXT UNIQUE,
                owner_token_hash TEXT UNIQUE NOT NULL,
                join_token_hash TEXT UNIQUE NOT NULL,
                author TEXT NOT NULL,
                protocol_revision TEXT NOT NULL,
                expected_nodes INTEGER NOT NULL DEFAULT 4,
                status TEXT NOT NULL DEFAULT 'collecting',
                public INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS local_offer_nodes (
                row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_public_id TEXT NOT NULL,
                node_public_id TEXT UNIQUE,
                token_hash TEXT UNIQUE NOT NULL,
                card_id TEXT NOT NULL,
                device_label TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'joined',
                result TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(room_public_id, card_id),
                FOREIGN KEY(room_public_id) REFERENCES local_offer_rooms(public_id)
            )
            """
        )
        db.execute(
            "CREATE INDEX IF NOT EXISTS local_offer_nodes_room "
            "ON local_offer_nodes(room_public_id, card_id)"
        )
        physical_node_columns = {
            row[1] for row in db.execute("PRAGMA table_info(physical_nodes)")
        }
        if "training_table" not in physical_node_columns:
            db.execute(
                "ALTER TABLE physical_nodes ADD COLUMN training_table TEXT NOT NULL DEFAULT '[]'"
            )
        public_ids = db.execute(
            "SELECT public_id FROM contributions WHERE status = 'public' ORDER BY row_id"
        ).fetchall()
        for (public_id,) in public_ids:
            record_publication_event(db, public_id)
        public_question_ids = db.execute(
            "SELECT public_id FROM questions WHERE status = 'public' ORDER BY row_id"
        ).fetchall()
        for (public_id,) in public_question_ids:
            record_question_publication_event(db, public_id)


def publication_event_id(db: sqlite3.Connection, object_type: str, object_id: str) -> str:
    row = db.execute(
        "SELECT event_id FROM events WHERE object_type = ? AND object_id = ? "
        "ORDER BY row_id LIMIT 1",
        (object_type, object_id),
    ).fetchone()
    return row[0] if row and row[0] else ""


def record_publication_event(db: sqlite3.Connection, public_id: str) -> None:
    db.row_factory = sqlite3.Row
    record = db.execute(
        "SELECT public_id, parent_public_id, relation, author, payload, updated_at "
        "FROM contributions WHERE public_id = ? AND status = 'public'",
        (public_id,),
    ).fetchone()
    if record is None:
        return
    payload = json.loads(record["payload"])
    links = []
    if record["parent_public_id"]:
        parent_type = "question" if record["parent_public_id"].startswith("Q") else "trace"
        link = {
            "relation": record["relation"] or "continues",
            "target_type": parent_type,
            "target_id": record["parent_public_id"],
        }
        target_event_id = publication_event_id(db, parent_type, record["parent_public_id"])
        if target_event_id:
            link["target_event_id"] = target_event_id
        links.append(link)
    event_type = {
        "continues": "trace_continued",
        "answers": "trace_answered",
    }.get(record["relation"], "trace_published")
    existing = db.execute(
        "SELECT 1 FROM events WHERE event_type = ? AND object_id = ?",
        (event_type, record["public_id"]),
    ).fetchone()
    if existing is not None:
        return
    cursor = db.execute(
        "INSERT INTO events "
        "(event_type, object_type, object_id, actor, links, payload, created_at) "
        "VALUES (?, 'trace', ?, ?, ?, ?, ?)",
        (
            event_type,
            record["public_id"],
            record["author"],
            json.dumps(links, ensure_ascii=False),
            json.dumps({"question": payload.get("question", "")}, ensure_ascii=False),
            record["updated_at"],
        ),
    )
    db.execute("UPDATE events SET event_id = ? WHERE row_id = ?", (f"E{cursor.lastrowid:06d}", cursor.lastrowid))


def record_question_publication_event(db: sqlite3.Connection, public_id: str) -> None:
    db.row_factory = sqlite3.Row
    record = db.execute(
        "SELECT public_id, source_trace_id, source_event_id, relation, author, payload, updated_at "
        "FROM questions WHERE public_id = ? AND status = 'public'",
        (public_id,),
    ).fetchone()
    if record is None:
        return
    existing = db.execute(
        "SELECT 1 FROM events WHERE event_type = 'question_opened' AND object_id = ?",
        (record["public_id"],),
    ).fetchone()
    if existing is not None:
        return
    link = {
        "relation": record["relation"] or "derives_from",
        "target_type": "trace",
        "target_id": record["source_trace_id"],
    }
    target_event_id = record["source_event_id"] or publication_event_id(
        db, "trace", record["source_trace_id"]
    )
    if target_event_id:
        link["target_event_id"] = target_event_id
        if not record["source_event_id"]:
            db.execute(
                "UPDATE questions SET source_event_id = ? WHERE public_id = ?",
                (target_event_id, record["public_id"]),
            )
    payload = json.loads(record["payload"])
    cursor = db.execute(
        "INSERT INTO events "
        "(event_type, object_type, object_id, actor, links, payload, created_at) "
        "VALUES ('question_opened', 'question', ?, ?, ?, ?, ?)",
        (
            record["public_id"],
            record["author"],
            json.dumps([link], ensure_ascii=False),
            json.dumps(
                {
                    "question": payload.get("question", ""),
                    "needed": payload.get("needed", ""),
                    "next_move": payload.get("next_move", "answer"),
                },
                ensure_ascii=False,
            ),
            record["updated_at"],
        ),
    )
    db.execute(
        "UPDATE events SET event_id = ? WHERE row_id = ?",
        (f"E{cursor.lastrowid:06d}", cursor.lastrowid),
    )


class RateLimiter:
    def __init__(self) -> None:
        self.events: dict[str, deque[float]] = defaultdict(deque)
        self.lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self.lock:
            events = self.events[key]
            while events and events[0] < now - RATE_WINDOW_SECONDS:
                events.popleft()
            if len(events) >= RATE_LIMIT:
                return False
            events.append(now)
            return True


class ApplicationHandler(SimpleHTTPRequestHandler):
    db_path: Path
    limiter = RateLimiter()

    def end_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("X-Frame-Options", "DENY")
        super().end_headers()

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/health":
            self.send_json(HTTPStatus.OK, {"ok": True})
            return
        if path == "/api/public/corpus.json":
            self.send_json(HTTPStatus.OK, self.public_corpus(), public=True)
            return
        if path == "/api/public/questions.json":
            self.get_public_questions("json")
            return
        if path in {"/api/public/questions.jsonl", "/data/questions.jsonl"}:
            self.get_public_questions("jsonl")
            return
        if path == "/api/public/records.json":
            self.get_public_records("json")
            return
        if path in {"/api/public/records.jsonl", "/data/traces.jsonl"}:
            self.get_public_records("jsonl")
            return
        if path == "/api/public/events.json":
            self.get_public_events("json")
            return
        if path in {"/api/public/events.jsonl", "/data/events.jsonl"}:
            self.get_public_events("jsonl")
            return
        if path == "/api/public/experiment-runs.json":
            self.send_json(
                HTTPStatus.OK,
                {"schema_version": "0.1", "runs": self.public_experiment_runs()},
                public=True,
                max_age=2,
            )
            return
        if path == "/api/public/attention.json":
            self.send_json(
                HTTPStatus.OK,
                {"schema_version": "0.1", "runs": self.public_attention_rooms()},
                public=True,
                max_age=2,
            )
            return
        if path == "/api/public/local-offers.json":
            self.send_json(
                HTTPStatus.OK,
                {"schema_version": "0.1", "runs": self.public_local_offer_rooms()},
                public=True,
                max_age=2,
            )
            return
        if path.startswith("/api/public/"):
            self.get_public(path.removeprefix("/api/public/"))
            return
        if path.rstrip("/") in SPA_ROUTES:
            original_path = self.path
            self.path = "/index.html"
            try:
                super().do_GET()
            finally:
                self.path = original_path
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        if not self.origin_allowed():
            self.send_json(HTTPStatus.FORBIDDEN, {"error": "origin not allowed"})
            return
        path = urlparse(self.path).path
        try:
            body = self.read_json()
            if path == "/api/contributions":
                self.create_contribution(body)
            elif path == "/api/contributions/status":
                self.get_status(body)
            elif path == "/api/contributions/append":
                self.append_response(body)
            elif path == "/api/questions":
                self.create_question(body)
            elif path == "/api/questions/status":
                self.get_question_status(body)
            elif path == "/api/experiment-runs":
                self.create_experiment_run(body)
            elif path == "/api/experiment-runs/status":
                self.get_experiment_run_status(body)
            elif path == "/api/experiment-runs/events":
                self.append_experiment_run_event(body)
            elif path == "/api/pocket-network/rooms":
                self.create_physical_room(body)
            elif path == "/api/pocket-network/join":
                self.join_physical_room(body)
            elif path == "/api/pocket-network/status":
                self.physical_status(body)
            elif path == "/api/pocket-network/ready":
                self.ready_physical_node(body)
            elif path == "/api/pocket-network/start":
                self.start_physical_room(body)
            elif path == "/api/pocket-network/contribute":
                self.contribute_physical_node(body)
            elif path == "/api/pocket-network/publish":
                self.publish_physical_room(body)
            elif path == "/api/attention/rooms":
                self.create_attention_room(body)
            elif path == "/api/attention/join":
                self.join_attention_room(body)
            elif path == "/api/attention/respond":
                self.respond_attention_node(body)
            elif path == "/api/attention/status":
                self.attention_status(body)
            elif path == "/api/attention/publish":
                self.publish_attention_room(body)
            elif path == "/api/local-offer/rooms":
                self.create_local_offer_room(body)
            elif path == "/api/local-offer/join":
                self.join_local_offer_room(body)
            elif path == "/api/local-offer/contribute":
                self.contribute_local_offer_node(body)
            elif path == "/api/local-offer/status":
                self.local_offer_status(body)
            elif path == "/api/local-offer/publish":
                self.publish_local_offer_room(body)
            else:
                self.send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
        except ValueError as error:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
        except sqlite3.Error:
            self.log_error("database error")
            self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "temporary storage error"})

    def origin_allowed(self) -> bool:
        origin = self.headers.get("Origin")
        return not origin or origin in ALLOWED_ORIGINS

    def client_key(self) -> str:
        forwarded = self.headers.get("X-Forwarded-For", "")
        return forwarded.split(",", 1)[0].strip() or self.client_address[0]

    def read_json(self) -> object:
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise ValueError("invalid content length") from error
        if size <= 0 or size > MAX_BODY:
            raise ValueError("invalid request size")
        try:
            return json.loads(self.rfile.read(size))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("invalid JSON") from error

    def create_contribution(self, body: object) -> None:
        if not self.limiter.allow(self.client_key()):
            self.send_json(HTTPStatus.TOO_MANY_REQUESTS, {"error": "too many submissions; try later"})
            return
        door, payload, author = validate_submission(body)
        parent_public_id = clean_text(
            body.get("parent_id", ""), "parent record", required=False, limit=40
        ).upper()
        requested_relation = clean_text(
            body.get("relation", ""), "relation", required=False, limit=20
        ).lower()
        relation = ""
        if parent_public_id:
            if not PUBLIC_ID_RE.fullmatch(parent_public_id):
                raise ValueError("parent record is not public")
            with sqlite3.connect(self.db_path) as db:
                if parent_public_id.startswith("T"):
                    parent = db.execute(
                        "SELECT 1 FROM contributions WHERE public_id = ? AND status = 'public'",
                        (parent_public_id,),
                    ).fetchone()
                    if parent is None:
                        raise ValueError("parent record is not public")
                    if door != "d04":
                        raise ValueError("only D04 traces can continue a conversation")
                    if requested_relation not in {"", "continues"}:
                        raise ValueError("invalid relation for trace parent")
                    relation = "continues"
                    payload["context_mode"] = "continued_conversations"
                else:
                    parent = db.execute(
                        "SELECT payload FROM questions WHERE public_id = ? AND status = 'public'",
                        (parent_public_id,),
                    ).fetchone()
                    if parent is None:
                        raise ValueError("parent record is not public")
                    if requested_relation not in {"", "answers"}:
                        raise ValueError("invalid relation for question parent")
                    parent_payload = json.loads(parent[0])
                    if payload["question"] != parent_payload.get("question"):
                        raise ValueError("question must match the public question exactly")
                    relation = "answers"
                    payload["question_id"] = parent_public_id
                    payload["context_mode"] = "answers_public_question"
        elif requested_relation:
            raise ValueError("relation requires a parent record")
        token = secrets.token_urlsafe(32)
        now = utc_now()
        with sqlite3.connect(self.db_path) as db:
            cursor = db.execute(
                "INSERT INTO contributions "
                "(token_hash, door, payload, author, parent_public_id, relation, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    token_hash(token),
                    door,
                    json.dumps(payload, ensure_ascii=False),
                    author,
                    parent_public_id,
                    relation,
                    now,
                    now,
                ),
            )
            public_id = f"T{cursor.lastrowid:04d}"
            db.execute("UPDATE contributions SET public_id = ? WHERE row_id = ?", (public_id, cursor.lastrowid))
        self.send_json(
            HTTPStatus.CREATED,
            {"id": public_id, "token": token, "status": "pending", "status_path": f"/contribution/#{token}"},
        )

    def create_question(self, body: object) -> None:
        if not self.limiter.allow(self.client_key()):
            self.send_json(HTTPStatus.TOO_MANY_REQUESTS, {"error": "too many submissions; try later"})
            return
        payload, author, source_trace_id = validate_question_submission(body)
        token = secrets.token_urlsafe(32)
        now = utc_now()
        with sqlite3.connect(self.db_path) as db:
            source = db.execute(
                "SELECT 1 FROM contributions WHERE public_id = ? AND status = 'public'",
                (source_trace_id,),
            ).fetchone()
            if source is None:
                raise ValueError("source trace is unavailable")
            source_event_id = publication_event_id(db, "trace", source_trace_id)
            if not source_event_id:
                record_publication_event(db, source_trace_id)
                source_event_id = publication_event_id(db, "trace", source_trace_id)
            cursor = db.execute(
                "INSERT INTO questions "
                "(token_hash, payload, author, source_trace_id, source_event_id, relation, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, 'derives_from', ?, ?)",
                (
                    token_hash(token),
                    json.dumps(payload, ensure_ascii=False),
                    author,
                    source_trace_id,
                    source_event_id,
                    now,
                    now,
                ),
            )
            public_id = f"Q{cursor.lastrowid:04d}"
            db.execute("UPDATE questions SET public_id = ? WHERE row_id = ?", (public_id, cursor.lastrowid))
        self.send_json(
            HTTPStatus.CREATED,
            {
                "id": public_id,
                "token": token,
                "status": "pending",
                "status_path": f"/question-submission/#{token}",
            },
        )

    def private_question(self, token: str) -> sqlite3.Row | None:
        if not isinstance(token, str) or len(token) > 200:
            return None
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            return db.execute(
                "SELECT public_id, payload, author, source_trace_id, source_event_id, relation, "
                "status, research_status, review_note, created_at, updated_at "
                "FROM questions WHERE token_hash = ?",
                (token_hash(token),),
            ).fetchone()

    def get_question_status(self, body: object) -> None:
        if not isinstance(body, dict):
            raise ValueError("invalid status request")
        record = self.private_question(body.get("token", ""))
        if record is None:
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "question not found"})
            return
        response = dict(record)
        response["payload"] = json.loads(response["payload"])
        if response["status"] == "public":
            response["public_path"] = f"/question/?id={response['public_id']}"
        self.send_json(HTTPStatus.OK, response)

    def private_record(self, token: str) -> sqlite3.Row | None:
        if not isinstance(token, str) or len(token) > 200:
            return None
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            return db.execute(
                "SELECT public_id, door, payload, author, parent_public_id, relation, status, review_note, created_at, updated_at "
                "FROM contributions WHERE token_hash = ?",
                (token_hash(token),),
            ).fetchone()

    def get_status(self, body: object) -> None:
        if not isinstance(body, dict):
            raise ValueError("invalid status request")
        record = self.private_record(body.get("token", ""))
        if record is None:
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "trace not found"})
            return
        response = dict(record)
        response["payload"] = json.loads(response["payload"])
        if response["status"] == "public":
            response["public_path"] = f"/record/?id={response['public_id']}"
        self.send_json(HTTPStatus.OK, response)

    def append_response(self, body: object) -> None:
        if not isinstance(body, dict):
            raise ValueError("invalid append request")
        token = body.get("token", "")
        response = validate_response(body.get("response"))
        hashed = token_hash(token) if isinstance(token, str) else ""
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            record = db.execute(
                "SELECT row_id, door, payload, status FROM contributions WHERE token_hash = ?", (hashed,)
            ).fetchone()
            if record is None:
                self.send_json(HTTPStatus.NOT_FOUND, {"error": "trace not found"})
                return
            if record["door"] != "d04" or record["status"] not in {"pending", "needs_changes"}:
                raise ValueError("this trace cannot accept another answer")
            payload = json.loads(record["payload"])
            if len(payload["responses"]) >= 12:
                raise ValueError("answer limit reached")
            payload["responses"].append(response)
            now = utc_now()
            db.execute(
                "UPDATE contributions SET payload = ?, status = 'pending', updated_at = ? WHERE row_id = ?",
                (json.dumps(payload, ensure_ascii=False), now, record["row_id"]),
            )
        self.send_json(HTTPStatus.OK, {"ok": True, "answers": len(payload["responses"])})

    def experiment_task_prompt(self, run_id: str) -> str:
        with sqlite3.connect(self.db_path) as db:
            row = db.execute(
                "SELECT experiment_id FROM experiment_runs WHERE public_id = ?", (run_id,)
            ).fetchone()
        experiment_id = row[0] if row else "E002"
        if experiment_id == "E003":
            return f"""You are continuing public laboratory run {run_id} for E003.

Goal H0001:
{MAIN_HYPOTHESIS['question']['en']}

Read experiments/E003-first-physical-swarm/PROTOCOL.md before changing code. E003 is a real-device control-plane test: three physical devices, three distinct locally updated toy weight matrices, atomic capsule batches, and one 4,096-class composed answer. Preserve the boundary that this is not yet a language model, the final neural ABI, a privacy proof, or evidence that H0001 is true.

Keep the work inspectable. Record failures and aggregate metrics, never private owner/join/node tokens, controlled tables, weights, or capsules. Do not publish a room result without the owner's explicit approval.
"""
        return f"""You are starting public laboratory run {run_id} for E002.

Goal H0001:
{MAIN_HYPOTHESIS['question']['en']}

Current phase: design and implement the smallest honest synthetic experiment. Read the repository's METHOD.md, hypotheses/H027-personal-delta-composition.md, the complete E001 record, and experiments/E002-synthetic-pocket-i-swarm/PROTOCOL.md before changing code.

The experiment must begin with two inspectable synthetic pocket i and then support N=2,4,8,16,32. Each i must actually update distinct personal weights from non-overlapping private data. Answers must have at least 256 possible values. Include controls that remove each i, remove z0, shuffle contributions, repeat the shared base, and expose the swarm scaling curve. Keep the protocol DRAFT until a human explicitly locks it. Do not claim the main hypothesis is proven by a synthetic result.

Privacy boundary: work only inside the selected public repository. Never inspect environment variables, credentials, browser data, private keys, home-directory files, or unrelated repositories. Never print or copy secrets. The public connector publishes filtered progress messages, plan text, action status, relative changed-file names, and metrics; it never publishes raw reasoning, command output, file contents, or environment data.

First, explain the proposed protocol and its falsification criteria in a concise plan. Then implement it with tests and an interactive, human-readable artifact. Preserve failed results.
"""

    def create_experiment_run(self, body: object) -> None:
        if not self.limiter.allow(self.client_key()):
            self.send_json(HTTPStatus.TOO_MANY_REQUESTS, {"error": "too many runs; try later"})
            return
        experiment_id, author, public_live = validate_experiment_run(body)
        token = secrets.token_urlsafe(32)
        now = utc_now()
        with sqlite3.connect(self.db_path) as db:
            cursor = db.execute(
                "INSERT INTO experiment_runs "
                "(token_hash, experiment_id, agent, author, public_live, protocol_version, created_at, updated_at) "
                "VALUES (?, ?, 'codex', ?, ?, ?, ?, ?)",
                (
                    token_hash(token),
                    experiment_id,
                    author,
                    1 if public_live else 0,
                    E002["protocol_version"] if experiment_id == "E002" else E003["protocol_version"],
                    now,
                    now,
                ),
            )
            public_id = f"R{cursor.lastrowid:04d}"
            db.execute(
                "UPDATE experiment_runs SET public_id = ? WHERE row_id = ?",
                (public_id, cursor.lastrowid),
            )
        self.send_json(
            HTTPStatus.CREATED,
            {
                "id": public_id,
                "token": token,
                "status": "created",
                "private_path": f"/experiment/connector/#{token}",
                "public_path": f"/experiment/run/?id={public_id}",
            },
        )

    def private_experiment_run(self, token: str) -> sqlite3.Row | None:
        if not isinstance(token, str) or len(token) > 200:
            return None
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            return db.execute(
                "SELECT public_id, experiment_id, agent, author, status, public_live, "
                "protocol_version, created_at, updated_at, completed_at "
                "FROM experiment_runs WHERE token_hash = ?",
                (token_hash(token),),
            ).fetchone()

    def get_experiment_run_status(self, body: object) -> None:
        if not isinstance(body, dict):
            raise ValueError("invalid run status request")
        record = self.private_experiment_run(body.get("token", ""))
        if record is None:
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "run not found"})
            return
        response = dict(record)
        response["public_live"] = bool(response["public_live"])
        response["public_path"] = f"/experiment/run/?id={response['public_id']}"
        response["experiment_path"] = f"/experiment/?id={response['experiment_id']}"
        response["task_prompt"] = self.experiment_task_prompt(response["public_id"])
        self.send_json(HTTPStatus.OK, response)

    def append_experiment_run_event(self, body: object) -> None:
        token, sequence, event_type, payload = validate_run_event(body)
        now = utc_now()
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            record = db.execute(
                "SELECT public_id, status FROM experiment_runs WHERE token_hash = ?",
                (token_hash(token),),
            ).fetchone()
            if record is None:
                self.send_json(HTTPStatus.NOT_FOUND, {"error": "run not found"})
                return
            if record["status"] in {"completed", "failed", "stopped"}:
                raise ValueError("run is already closed")
            try:
                db.execute(
                    "INSERT INTO experiment_run_events "
                    "(run_public_id, sequence, event_type, payload, created_at) VALUES (?, ?, ?, ?, ?)",
                    (
                        record["public_id"],
                        sequence,
                        event_type,
                        json.dumps(payload, ensure_ascii=False),
                        now,
                    ),
                )
            except sqlite3.IntegrityError:
                existing = db.execute(
                    "SELECT event_type, payload FROM experiment_run_events "
                    "WHERE run_public_id = ? AND sequence = ?",
                    (record["public_id"], sequence),
                ).fetchone()
                canonical = json.dumps(payload, ensure_ascii=False)
                if existing and existing["event_type"] == event_type and existing["payload"] == canonical:
                    self.send_json(HTTPStatus.OK, {"ok": True, "duplicate": True})
                    return
                raise ValueError("event sequence already exists")
            status = "running"
            completed_at = ""
            if event_type == "run_completed":
                status = str(payload["status"])
                completed_at = now
            db.execute(
                "UPDATE experiment_runs SET status = ?, updated_at = ?, completed_at = ? "
                "WHERE public_id = ?",
                (status, now, completed_at, record["public_id"]),
            )
        self.send_json(HTTPStatus.CREATED, {"ok": True, "sequence": sequence})

    def public_run_events(self, run_id: str) -> list[dict]:
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute(
                "SELECT sequence, event_type, payload, created_at "
                "FROM experiment_run_events WHERE run_public_id = ? ORDER BY sequence",
                (run_id,),
            ).fetchall()
        events = []
        for row in rows:
            event = dict(row)
            event["payload"] = json.loads(event["payload"])
            events.append(event)
        return events

    def public_experiment_run(self, run_id: str, *, include_events: bool = True) -> dict | None:
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            row = db.execute(
                "SELECT public_id, experiment_id, agent, author, status, protocol_version, "
                "created_at, updated_at, completed_at FROM experiment_runs "
                "WHERE public_id = ? AND public_live = 1",
                (run_id,),
            ).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["object_type"] = "experiment_run"
        if include_events:
            result["events"] = self.public_run_events(run_id)
        return result

    def public_experiment_runs(self, experiment_id: str = "") -> list[dict]:
        query = (
            "SELECT public_id FROM experiment_runs WHERE public_live = 1 "
            + ("AND experiment_id = ? " if experiment_id else "")
            + "ORDER BY row_id DESC"
        )
        with sqlite3.connect(self.db_path) as db:
            params = (experiment_id,) if experiment_id else ()
            ids = [row[0] for row in db.execute(query, params).fetchall()]
        return [self.public_experiment_run(run_id, include_events=False) for run_id in ids]

    def get_public_experiment(self) -> None:
        response = dict(E002)
        response["object_type"] = "experiment"
        response["hypothesis"] = MAIN_HYPOTHESIS
        response["runs"] = self.public_experiment_runs("E002")
        self.send_json(HTTPStatus.OK, response, public=True, max_age=2)

    def create_physical_room(self, body: object) -> None:
        if not self.limiter.allow(self.client_key()):
            self.send_json(HTTPStatus.TOO_MANY_REQUESTS, {"error": "too many rooms; try later"})
            return
        if not isinstance(body, dict) or body.get("consent") is not True:
            raise ValueError("private room consent is required")
        author = validate_author(body)
        owner_token = secrets.token_urlsafe(32)
        join_token = secrets.token_urlsafe(24)
        now = utc_now()
        with sqlite3.connect(self.db_path) as db:
            cursor = db.execute(
                "INSERT INTO physical_rooms "
                "(owner_token_hash, join_token_hash, author, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (token_hash(owner_token), token_hash(join_token), author, now, now),
            )
            room_id = f"N{cursor.lastrowid:04d}"
            db.execute(
                "UPDATE physical_rooms SET public_id = ? WHERE row_id = ?",
                (room_id, cursor.lastrowid),
            )
        self.send_json(
            HTTPStatus.CREATED,
            {
                "room_id": room_id,
                "owner_token": owner_token,
                "join_token": join_token,
                "owner_path": f"/network/#owner={owner_token}",
                "join_path": f"/network/#join={join_token}",
            },
        )

    def join_physical_room(self, body: object) -> None:
        if not isinstance(body, dict):
            raise ValueError("invalid join request")
        join_token = clean_text(body.get("join_token", ""), "join token", limit=200)
        label = clean_text(body.get("label", "device"), "device label", limit=40)
        now = utc_now()
        node_token = secrets.token_urlsafe(32)
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            db.execute("BEGIN IMMEDIATE")
            room = db.execute(
                "SELECT public_id, status FROM physical_rooms WHERE join_token_hash = ?",
                (token_hash(join_token),),
            ).fetchone()
            if room is None:
                self.send_json(HTTPStatus.NOT_FOUND, {"error": "room not found"})
                return
            if room["status"] != "waiting":
                raise ValueError("room is no longer accepting devices")
            roles = {
                row[0]
                for row in db.execute(
                    "SELECT role FROM physical_nodes WHERE room_public_id = ?", (room["public_id"],)
                ).fetchall()
            }
            available = [role for role in range(3) if role not in roles]
            if not available:
                raise ValueError("all three device slots are occupied")
            role = available[0]
            training_table = new_physical_table()
            cursor = db.execute(
                "INSERT INTO physical_nodes "
                "(room_public_id, token_hash, role, label, training_table, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    room["public_id"], token_hash(node_token), role, label,
                    json.dumps(training_table), now, now,
                ),
            )
            node_id = f"{room['public_id']}-I{role + 1}"
            db.execute(
                "UPDATE physical_nodes SET node_public_id = ? WHERE row_id = ?",
                (node_id, cursor.lastrowid),
            )
        self.send_json(
            HTTPStatus.CREATED,
            {
                "room_id": room["public_id"],
                "node_id": node_id,
                "node_token": node_token,
                "role": role,
                "training_table": training_table,
                "node_path": f"/network/#node={node_token}",
            },
        )

    def physical_access(self, token: object) -> tuple[str, sqlite3.Row, sqlite3.Row | None] | None:
        if not isinstance(token, str) or len(token) > 200:
            return None
        digest = token_hash(token)
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            room = db.execute(
                "SELECT * FROM physical_rooms WHERE owner_token_hash = ?", (digest,)
            ).fetchone()
            if room is not None:
                return "owner", room, None
            node = db.execute(
                "SELECT * FROM physical_nodes WHERE token_hash = ?", (digest,)
            ).fetchone()
            if node is None:
                return None
            room = db.execute(
                "SELECT * FROM physical_rooms WHERE public_id = ?", (node["room_public_id"],)
            ).fetchone()
            return ("node", room, node) if room else None

    def physical_status(self, body: object) -> None:
        if not isinstance(body, dict):
            raise ValueError("invalid status request")
        access = self.physical_access(body.get("token"))
        if access is None:
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "room access not found"})
            return
        kind, room, node = access
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            nodes = db.execute(
                "SELECT node_public_id, role, label, status, metrics, created_at, updated_at "
                "FROM physical_nodes WHERE room_public_id = ? ORDER BY role",
                (room["public_id"],),
            ).fetchall()
        response = {
            "access": kind,
            "room_id": room["public_id"],
            "author": room["author"],
            "status": room["status"],
            "task_count": room["task_count"],
            "nodes": [
                {**dict(item), "metrics": json.loads(item["metrics"])} for item in nodes
            ],
            "result": json.loads(room["result"]),
            "public": bool(room["public"]),
        }
        if node is not None:
            tasks = json.loads(room["tasks"])
            response.update(
                {
                    "node_id": node["node_public_id"],
                    "role": node["role"],
                    "label": node["label"],
                    "node_status": node["status"],
                    "training_table": json.loads(node["training_table"]),
                    "task_keys": [task[node["role"]] for task in tasks],
                }
            )
        self.send_json(HTTPStatus.OK, response)

    def ready_physical_node(self, body: object) -> None:
        if not isinstance(body, dict):
            raise ValueError("invalid ready request")
        access = self.physical_access(body.get("node_token"))
        if access is None or access[0] != "node" or access[2] is None:
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "node not found"})
            return
        _, room, node = access
        if room["status"] != "waiting":
            raise ValueError("training phase is closed")
        metrics_value = body.get("metrics")
        if not isinstance(metrics_value, dict):
            raise ValueError("training metrics are required")
        accuracy = metrics_value.get("accuracy")
        delta_norm = metrics_value.get("delta_norm")
        if not isinstance(accuracy, (int, float)) or not 0 <= float(accuracy) <= 1:
            raise ValueError("invalid local accuracy")
        if not isinstance(delta_norm, (int, float)) or not math.isfinite(float(delta_norm)):
            raise ValueError("invalid weight delta norm")
        metrics = {
            "accuracy": float(accuracy),
            "delta_norm": min(abs(float(delta_norm)), 1_000_000),
            "weight_checksum": clean_text(
                metrics_value.get("weight_checksum", ""), "weight checksum", limit=128
            ),
            "runtime": clean_text(metrics_value.get("runtime", "browser"), "runtime", limit=80),
        }
        now = utc_now()
        with sqlite3.connect(self.db_path) as db:
            db.execute(
                "UPDATE physical_nodes SET status = 'ready', metrics = ?, updated_at = ? "
                "WHERE row_id = ?",
                (json.dumps(metrics, sort_keys=True), now, node["row_id"]),
            )
            db.execute(
                "UPDATE physical_rooms SET updated_at = ? WHERE public_id = ?",
                (now, room["public_id"]),
            )
        self.send_json(HTTPStatus.OK, {"ok": True, "node_id": node["node_public_id"]})

    def start_physical_room(self, body: object) -> None:
        if not isinstance(body, dict):
            raise ValueError("invalid start request")
        access = self.physical_access(body.get("owner_token"))
        if access is None or access[0] != "owner":
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "room not found"})
            return
        room = access[1]
        count = body.get("task_count", 64)
        if not isinstance(count, int) or isinstance(count, bool) or not 16 <= count <= 256:
            raise ValueError("choose between 16 and 256 tasks")
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            statuses = db.execute(
                "SELECT status FROM physical_nodes WHERE room_public_id = ? ORDER BY role",
                (room["public_id"],),
            ).fetchall()
            if len(statuses) != 3 or any(row["status"] != "ready" for row in statuses):
                raise ValueError("all three devices must finish local training first")
            tasks = physical_tasks(room["public_id"], count)
            now = utc_now()
            db.execute(
                "UPDATE physical_rooms SET status = 'running', task_count = ?, tasks = ?, "
                "updated_at = ? WHERE public_id = ? AND status = 'waiting'",
                (count, json.dumps(tasks), now, room["public_id"]),
            )
        self.send_json(HTTPStatus.OK, {"ok": True, "tasks": count})

    def calculate_physical_result(self, db: sqlite3.Connection, room_id: str) -> dict | None:
        db.row_factory = sqlite3.Row
        room = db.execute(
            "SELECT * FROM physical_rooms WHERE public_id = ?", (room_id,)
        ).fetchone()
        nodes = db.execute(
            "SELECT role, training_table, contribution FROM physical_nodes "
            "WHERE room_public_id = ? ORDER BY role",
            (room_id,),
        ).fetchall()
        if room is None or len(nodes) != 3 or any(not json.loads(node["contribution"]) for node in nodes):
            return None
        tasks = json.loads(room["tasks"])
        batches = {node["role"]: json.loads(node["contribution"]) for node in nodes}
        tables = {node["role"]: json.loads(node["training_table"]) for node in nodes}
        exact = 0
        role_correct = [0, 0, 0]
        remove_correct = [0, 0, 0]
        for index, keys in enumerate(tasks):
            expected_digits = [tables[role][keys[role]] for role in range(3)]
            predicted = [
                max(range(16), key=lambda item: batches[role][index][item]) for role in range(3)
            ]
            role_correct = [
                role_correct[role] + int(predicted[role] == expected_digits[role])
                for role in range(3)
            ]
            exact += int(predicted == expected_digits)
            for removed in range(3):
                ablated = predicted.copy()
                ablated[removed] = 0
                remove_correct[removed] += int(ablated == expected_digits)
        count = len(tasks)
        return {
            "task_count": count,
            "answer_space": 4096,
            "random_guess_probability": 1 / 4096,
            "exact_accuracy": exact / count,
            "per_node_accuracy": [value / count for value in role_correct],
            "remove_one_accuracy": [value / count for value in remove_correct],
            "all_three_complete": True,
            "claim_boundary": E003["claim_boundary"],
        }

    def contribute_physical_node(self, body: object) -> None:
        if not isinstance(body, dict):
            raise ValueError("invalid contribution request")
        access = self.physical_access(body.get("node_token"))
        if access is None or access[0] != "node" or access[2] is None:
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "node not found"})
            return
        _, room, node = access
        if room["status"] != "running":
            raise ValueError("room is not running")
        batch = validate_logits(body.get("capsules"), room["task_count"])
        now = utc_now()
        with sqlite3.connect(self.db_path) as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "UPDATE physical_nodes SET status = 'complete', contribution = ?, updated_at = ? "
                "WHERE row_id = ?",
                (json.dumps(batch), now, node["row_id"]),
            )
            result = self.calculate_physical_result(db, room["public_id"])
            if result is not None:
                db.execute(
                    "UPDATE physical_rooms SET status = 'complete', result = ?, updated_at = ? "
                    "WHERE public_id = ?",
                    (json.dumps(result), now, room["public_id"]),
                )
        self.send_json(HTTPStatus.OK, {"ok": True, "node_id": node["node_public_id"]})

    def publish_physical_room(self, body: object) -> None:
        if not isinstance(body, dict) or body.get("consent") is not True:
            raise ValueError("publication consent is required")
        access = self.physical_access(body.get("owner_token"))
        if access is None or access[0] != "owner":
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "room not found"})
            return
        room = access[1]
        if room["status"] != "complete":
            raise ValueError("the physical run is not complete")
        with sqlite3.connect(self.db_path) as db:
            db.execute(
                "UPDATE physical_rooms SET public = 1, updated_at = ? WHERE public_id = ?",
                (utc_now(), room["public_id"]),
            )
        self.send_json(HTTPStatus.OK, {"ok": True, "public_path": f"/network/?id={room['public_id']}"})

    def public_physical_rooms(self) -> list[dict]:
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute(
                "SELECT public_id, author, status, task_count, result, created_at, updated_at "
                "FROM physical_rooms WHERE public = 1 ORDER BY row_id DESC"
            ).fetchall()
        return [{**dict(row), "result": json.loads(row["result"])} for row in rows]

    def get_public_e003(self) -> None:
        response = dict(E003)
        response["object_type"] = "experiment"
        response["hypothesis"] = MAIN_HYPOTHESIS
        response["runs"] = self.public_physical_rooms()
        response["codex_runs"] = self.public_experiment_runs("E003")
        self.send_json(HTTPStatus.OK, response, public=True, max_age=2)

    def get_public_e004(self) -> None:
        response = dict(E004)
        response["object_type"] = "experiment"
        response["hypothesis"] = MAIN_HYPOTHESIS
        response["runs"] = self.public_experiment_runs("E004")
        self.send_json(HTTPStatus.OK, response, public=True, max_age=2)

    def create_attention_room(self, body: object) -> None:
        if not self.limiter.allow(self.client_key()):
            self.send_json(HTTPStatus.TOO_MANY_REQUESTS, {"error": "too many rooms; try later"})
            return
        if not isinstance(body, dict) or body.get("consent") is not True:
            raise ValueError("private attention room consent is required")
        question = clean_text(body.get("question", ""), "question", limit=4_000)
        author = validate_author(body)
        owner_token = secrets.token_urlsafe(32)
        join_token = secrets.token_urlsafe(24)
        question_hash = hashlib.sha256(question.encode("utf-8")).hexdigest()
        now = utc_now()
        with sqlite3.connect(self.db_path) as db:
            cursor = db.execute(
                "INSERT INTO attention_rooms "
                "(owner_token_hash, join_token_hash, author, question, question_hash, "
                "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    token_hash(owner_token),
                    token_hash(join_token),
                    author,
                    question,
                    question_hash,
                    now,
                    now,
                ),
            )
            public_id = f"A{cursor.lastrowid:04d}"
            db.execute(
                "UPDATE attention_rooms SET public_id = ? WHERE row_id = ?",
                (public_id, cursor.lastrowid),
            )
        self.send_json(
            HTTPStatus.CREATED,
            {
                "room_id": public_id,
                "owner_token": owner_token,
                "join_token": join_token,
                "question_hash": question_hash,
                "status": "collecting",
            },
        )

    def join_attention_room(self, body: object) -> None:
        if not isinstance(body, dict):
            raise ValueError("invalid attention join request")
        join_token = body.get("join_token")
        if not isinstance(join_token, str) or len(join_token) > 200:
            raise ValueError("invalid join token")
        card_id = clean_text(body.get("card_id", ""), "card id", limit=20).upper()
        card = ATTENTION_CARDS.get(card_id)
        if card is None:
            raise ValueError("unknown locked capability card")
        device_label = clean_text(body.get("device_label", ""), "device label", limit=40)
        if device_label != card["device"]:
            raise ValueError("card belongs to another declared device")
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            room = db.execute(
                "SELECT * FROM attention_rooms WHERE join_token_hash = ?",
                (token_hash(join_token),),
            ).fetchone()
            if room is None:
                self.send_json(HTTPStatus.NOT_FOUND, {"error": "attention room not found"})
                return
            if room["status"] != "collecting":
                raise ValueError("attention room is closed")
            existing = db.execute(
                "SELECT node_public_id FROM attention_nodes "
                "WHERE room_public_id = ? AND card_id = ?",
                (room["public_id"], card_id),
            ).fetchone()
            if existing is not None:
                raise ValueError("this capability card already joined")
            node_token = secrets.token_urlsafe(32)
            now = utc_now()
            cursor = db.execute(
                "INSERT INTO attention_nodes "
                "(room_public_id, token_hash, card_id, device_label, card_revision, "
                "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    room["public_id"],
                    token_hash(node_token),
                    card_id,
                    device_label,
                    ATTENTION_CARD_REVISION,
                    now,
                    now,
                ),
            )
            node_id = f"{room['public_id']}-{card_id}"
            db.execute(
                "UPDATE attention_nodes SET node_public_id = ? WHERE row_id = ?",
                (node_id, cursor.lastrowid),
            )
        self.send_json(
            HTTPStatus.CREATED,
            {
                "room_id": room["public_id"],
                "node_id": node_id,
                "node_token": node_token,
                "card_id": card_id,
                "card_revision": ATTENTION_CARD_REVISION,
                "question": room["question"],
                "question_hash": room["question_hash"],
            },
        )

    def attention_node_access(self, token: object) -> tuple[sqlite3.Row, sqlite3.Row] | None:
        if not isinstance(token, str) or len(token) > 200:
            return None
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            node = db.execute(
                "SELECT * FROM attention_nodes WHERE token_hash = ?", (token_hash(token),)
            ).fetchone()
            if node is None:
                return None
            room = db.execute(
                "SELECT * FROM attention_rooms WHERE public_id = ?", (node["room_public_id"],)
            ).fetchone()
        return (room, node) if room else None

    def respond_attention_node(self, body: object) -> None:
        if not isinstance(body, dict):
            raise ValueError("invalid attention response")
        access = self.attention_node_access(body.get("node_token"))
        if access is None:
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "attention node not found"})
            return
        room, node = access
        if room["status"] != "collecting":
            raise ValueError("attention room is closed")
        if body.get("question_hash") != room["question_hash"]:
            raise ValueError("question changed in transit")
        vector_score = body.get("whole_text_vector")
        exact_score = body.get("exact_terms")
        latency_ms = body.get("latency_ms")
        if any(
            not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value)
            for value in (vector_score, exact_score, latency_ms)
        ):
            raise ValueError("attention scores and latency must be finite numbers")
        if not 0 <= float(vector_score) <= 1 or not 0 <= float(exact_score) <= 1:
            raise ValueError("attention score is outside [0, 1]")
        if not 0 <= float(latency_ms) <= 600_000:
            raise ValueError("invalid attention latency")
        matched_terms = body.get("matched_terms", [])
        if not isinstance(matched_terms, list) or len(matched_terms) > 40:
            raise ValueError("invalid matched terms")
        response = {
            "question_hash": room["question_hash"],
            "whole_text_vector": round(float(vector_score), 6),
            "exact_terms": round(float(exact_score), 6),
            "matched_terms": [clean_text(item, "matched term", limit=80) for item in matched_terms],
            "latency_ms": round(float(latency_ms), 3),
            "client_version": clean_text(body.get("client_version", ""), "client version", limit=40),
        }
        now = utc_now()
        with sqlite3.connect(self.db_path) as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "UPDATE attention_nodes SET status = 'complete', response = ?, updated_at = ? "
                "WHERE row_id = ?",
                (json.dumps(response, ensure_ascii=False, sort_keys=True), now, node["row_id"]),
            )
            completed = db.execute(
                "SELECT COUNT(*) FROM attention_nodes "
                "WHERE room_public_id = ? AND status = 'complete'",
                (room["public_id"],),
            ).fetchone()[0]
            if completed == room["expected_nodes"]:
                db.execute(
                    "UPDATE attention_rooms SET status = 'complete', updated_at = ? WHERE public_id = ?",
                    (now, room["public_id"]),
                )
            else:
                db.execute(
                    "UPDATE attention_rooms SET updated_at = ? WHERE public_id = ?",
                    (now, room["public_id"]),
                )
        self.send_json(HTTPStatus.OK, {"ok": True, "node_id": node["node_public_id"]})

    def attention_room_payload(self, room: sqlite3.Row) -> dict:
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            nodes = db.execute(
                "SELECT node_public_id, card_id, device_label, card_revision, status, response, "
                "created_at, updated_at FROM attention_nodes WHERE room_public_id = ? ORDER BY card_id",
                (room["public_id"],),
            ).fetchall()
        return {
            "schema_version": "0.1",
            "experiment_id": "E007",
            "checkpoint": "3A",
            "room_id": room["public_id"],
            "status": room["status"],
            "question": room["question"],
            "question_hash": room["question_hash"],
            "expected_nodes": room["expected_nodes"],
            "nodes": [
                {**dict(node), "response": json.loads(node["response"])} for node in nodes
            ],
            "created_at": room["created_at"],
            "updated_at": room["updated_at"],
            "claim_boundary": "Attention delivery and card ranking only; no Qwen, memory, RAG, training, or answers.",
        }

    def attention_status(self, body: object) -> None:
        if not isinstance(body, dict):
            raise ValueError("invalid attention status request")
        token = body.get("owner_token")
        if not isinstance(token, str) or len(token) > 200:
            raise ValueError("invalid owner token")
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            room = db.execute(
                "SELECT * FROM attention_rooms WHERE owner_token_hash = ?", (token_hash(token),)
            ).fetchone()
        if room is None:
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "attention room not found"})
            return
        self.send_json(HTTPStatus.OK, self.attention_room_payload(room))

    def publish_attention_room(self, body: object) -> None:
        if not isinstance(body, dict) or body.get("consent") is not True:
            raise ValueError("publication consent is required")
        token = body.get("owner_token")
        if not isinstance(token, str) or len(token) > 200:
            raise ValueError("invalid owner token")
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            room = db.execute(
                "SELECT * FROM attention_rooms WHERE owner_token_hash = ?", (token_hash(token),)
            ).fetchone()
            if room is None:
                self.send_json(HTTPStatus.NOT_FOUND, {"error": "attention room not found"})
                return
            if room["status"] != "complete":
                raise ValueError("all four attention receipts are required before publication")
            db.execute(
                "UPDATE attention_rooms SET public = 1, updated_at = ? WHERE public_id = ?",
                (utc_now(), room["public_id"]),
            )
        self.send_json(
            HTTPStatus.OK,
            {"ok": True, "public_path": f"/api/public/{room['public_id']}"},
        )

    def public_attention_rooms(self) -> list[dict]:
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            rooms = db.execute(
                "SELECT * FROM attention_rooms WHERE public = 1 ORDER BY row_id DESC"
            ).fetchall()
        return [self.attention_room_payload(room) for room in rooms]

    def create_local_offer_room(self, body: object) -> None:
        if not self.limiter.allow(self.client_key()):
            self.send_json(HTTPStatus.TOO_MANY_REQUESTS, {"error": "too many rooms; try later"})
            return
        if not isinstance(body, dict) or body.get("consent") is not True:
            raise ValueError("private local-offer room consent is required")
        author = validate_author(body)
        owner_token = secrets.token_urlsafe(32)
        join_token = secrets.token_urlsafe(24)
        now = utc_now()
        with sqlite3.connect(self.db_path) as db:
            cursor = db.execute(
                "INSERT INTO local_offer_rooms "
                "(owner_token_hash, join_token_hash, author, protocol_revision, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    token_hash(owner_token),
                    token_hash(join_token),
                    author,
                    LOCAL_OFFER_REVISION,
                    now,
                    now,
                ),
            )
            public_id = f"L{cursor.lastrowid:04d}"
            db.execute(
                "UPDATE local_offer_rooms SET public_id = ? WHERE row_id = ?",
                (public_id, cursor.lastrowid),
            )
        self.send_json(
            HTTPStatus.CREATED,
            {
                "room_id": public_id,
                "owner_token": owner_token,
                "join_token": join_token,
                "protocol_revision": LOCAL_OFFER_REVISION,
                "status": "collecting",
            },
        )

    def join_local_offer_room(self, body: object) -> None:
        if not isinstance(body, dict):
            raise ValueError("invalid local-offer join request")
        join_token = body.get("join_token")
        if not isinstance(join_token, str) or len(join_token) > 200:
            raise ValueError("invalid join token")
        card_id = clean_text(body.get("card_id", ""), "card id", limit=20).upper()
        card = ATTENTION_CARDS.get(card_id)
        if card is None:
            raise ValueError("unknown locked capability card")
        device_label = clean_text(body.get("device_label", ""), "device label", limit=40)
        if device_label != card["device"]:
            raise ValueError("card belongs to another declared device")
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            room = db.execute(
                "SELECT * FROM local_offer_rooms WHERE join_token_hash = ?",
                (token_hash(join_token),),
            ).fetchone()
            if room is None:
                self.send_json(HTTPStatus.NOT_FOUND, {"error": "local-offer room not found"})
                return
            if room["status"] != "collecting":
                raise ValueError("local-offer room is closed")
            existing = db.execute(
                "SELECT * FROM local_offer_nodes WHERE room_public_id = ? AND card_id = ?",
                (room["public_id"], card_id),
            ).fetchone()
            if existing is not None and existing["status"] == "complete":
                raise ValueError("this local library already completed")
            node_token = secrets.token_urlsafe(32)
            now = utc_now()
            if existing is None:
                cursor = db.execute(
                    "INSERT INTO local_offer_nodes "
                    "(room_public_id, token_hash, card_id, device_label, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        room["public_id"],
                        token_hash(node_token),
                        card_id,
                        device_label,
                        now,
                        now,
                    ),
                )
                node_id = f"{room['public_id']}-{card_id}"
                db.execute(
                    "UPDATE local_offer_nodes SET node_public_id = ? WHERE row_id = ?",
                    (node_id, cursor.lastrowid),
                )
            else:
                node_id = existing["node_public_id"]
                db.execute(
                    "UPDATE local_offer_nodes SET token_hash = ?, updated_at = ? WHERE row_id = ?",
                    (token_hash(node_token), now, existing["row_id"]),
                )
        questions = [
            {
                "id": question_id,
                "question": question,
                "question_hash": hashlib.sha256(question.encode("utf-8")).hexdigest(),
            }
            for question_id, question in LOCAL_OFFER_QUESTIONS.items()
        ]
        self.send_json(
            HTTPStatus.CREATED,
            {
                "room_id": room["public_id"],
                "node_id": node_id,
                "node_token": node_token,
                "card_id": card_id,
                "protocol_revision": room["protocol_revision"],
                "questions": questions,
            },
        )

    def local_offer_node_access(self, token: object) -> tuple[sqlite3.Row, sqlite3.Row] | None:
        if not isinstance(token, str) or len(token) > 200:
            return None
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            node = db.execute(
                "SELECT * FROM local_offer_nodes WHERE token_hash = ?", (token_hash(token),)
            ).fetchone()
            if node is None:
                return None
            room = db.execute(
                "SELECT * FROM local_offer_rooms WHERE public_id = ?", (node["room_public_id"],)
            ).fetchone()
        return (room, node) if room else None

    def validate_local_offer_batch(self, body: dict) -> dict:
        if body.get("memory_revision") != "e007-local-memory-v0.1":
            raise ValueError("wrong local-memory revision")
        lane_config = body.get("lane_config")
        if not isinstance(lane_config, dict) or set(lane_config) != LOCAL_OFFER_LANES:
            raise ValueError("all three locked search lanes are required")
        clean_lane_config = {}
        for lane, config in lane_config.items():
            if not isinstance(config, dict):
                raise ValueError("invalid search lane configuration")
            threshold = config.get("threshold")
            calibration_f1 = config.get("calibration_f1")
            if any(
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(float(value))
                for value in (threshold, calibration_f1)
            ):
                raise ValueError("invalid calibrated search values")
            if not -1 <= float(threshold) <= 1 or not 0 <= float(calibration_f1) <= 1:
                raise ValueError("calibrated search value is outside its range")
            clean_lane_config[lane] = {
                "threshold": round(float(threshold), 6),
                "calibration_f1": round(float(calibration_f1), 6),
            }
        results = body.get("results")
        expected_count = len(LOCAL_OFFER_QUESTIONS) * len(LOCAL_OFFER_LANES)
        if not isinstance(results, list) or len(results) != expected_count:
            raise ValueError("one result per question and lane is required")
        cleaned = []
        seen = set()
        for item in results:
            if not isinstance(item, dict):
                raise ValueError("invalid local-offer result")
            question_id = clean_text(item.get("question_id", ""), "question id", limit=10).upper()
            lane = clean_text(item.get("lane", ""), "search lane", limit=40)
            if question_id not in LOCAL_OFFER_QUESTIONS or lane not in LOCAL_OFFER_LANES:
                raise ValueError("unknown question or search lane")
            key = (question_id, lane)
            if key in seen:
                raise ValueError("duplicate question and lane result")
            seen.add(key)
            expected_hash = hashlib.sha256(
                LOCAL_OFFER_QUESTIONS[question_id].encode("utf-8")
            ).hexdigest()
            if item.get("question_hash") != expected_hash:
                raise ValueError("question changed in transit")
            status = clean_text(item.get("status", ""), "result status", limit=20)
            if status not in LOCAL_OFFER_STATUSES:
                raise ValueError("invalid local-offer status")
            score = item.get("score")
            if not isinstance(score, (int, float)) or isinstance(score, bool) or not math.isfinite(float(score)):
                raise ValueError("invalid local search score")
            if not -1 <= float(score) <= 1:
                raise ValueError("local search score is outside [-1, 1]")
            source_id = clean_text(
                item.get("source_id", ""), "source id", required=False, limit=40
            )
            capsule_value = item.get("capsule")
            capsule = None
            if status == "found":
                if not source_id or not isinstance(capsule_value, dict):
                    raise ValueError("found requires a source and capsule")
                capsule = {
                    "claim": clean_text(capsule_value.get("claim", ""), "claim", limit=2_000),
                    "evidence": clean_text(capsule_value.get("evidence", ""), "evidence", limit=4_000),
                    "source": clean_text(capsule_value.get("source", ""), "source", limit=500),
                    "source_lineage": clean_text(
                        capsule_value.get("source_lineage", ""), "source lineage", limit=200
                    ),
                    "conditions": clean_text(
                        capsule_value.get("conditions", ""), "conditions", limit=2_000
                    ),
                    "limitations": clean_text(
                        capsule_value.get("limitations", ""), "limitations", limit=2_000
                    ),
                    "permission": clean_text(
                        capsule_value.get("permission", ""), "permission", limit=100
                    ),
                }
            elif capsule_value not in (None, {}):
                raise ValueError("only found may send a capsule")
            canary_hash = clean_text(
                item.get("canary_hash", ""), "canary hash", required=False, limit=64
            ).lower()
            if canary_hash and not re.fullmatch(r"[0-9a-f]{64}", canary_hash):
                raise ValueError("invalid canary hash")
            cleaned.append(
                {
                    "question_id": question_id,
                    "question_hash": expected_hash,
                    "lane": lane,
                    "status": status,
                    "score": round(float(score), 6),
                    "source_id": source_id,
                    "capsule": capsule,
                    "canary_hash": canary_hash,
                }
            )
        return {
            "client_version": clean_text(body.get("client_version", ""), "client version", limit=80),
            "runtime": clean_text(body.get("runtime", ""), "runtime", limit=120),
            "memory_revision": "e007-local-memory-v0.1",
            "model": clean_text(body.get("model", ""), "model", limit=200),
            "model_revision": clean_text(
                body.get("model_revision", ""), "model revision", limit=80
            ),
            "lane_config": clean_lane_config,
            "results": sorted(cleaned, key=lambda item: (item["question_id"], item["lane"])),
        }

    def contribute_local_offer_node(self, body: object) -> None:
        if not isinstance(body, dict):
            raise ValueError("invalid local-offer contribution")
        access = self.local_offer_node_access(body.get("node_token"))
        if access is None:
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "local-offer node not found"})
            return
        room, node = access
        if room["status"] != "collecting":
            raise ValueError("local-offer room is closed")
        result = self.validate_local_offer_batch(body)
        now = utc_now()
        with sqlite3.connect(self.db_path) as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "UPDATE local_offer_nodes SET status = 'complete', result = ?, updated_at = ? "
                "WHERE row_id = ?",
                (json.dumps(result, ensure_ascii=False, sort_keys=True), now, node["row_id"]),
            )
            completed = db.execute(
                "SELECT COUNT(*) FROM local_offer_nodes "
                "WHERE room_public_id = ? AND status = 'complete'",
                (room["public_id"],),
            ).fetchone()[0]
            if completed == room["expected_nodes"]:
                db.execute(
                    "UPDATE local_offer_rooms SET status = 'complete', updated_at = ? WHERE public_id = ?",
                    (now, room["public_id"]),
                )
            else:
                db.execute(
                    "UPDATE local_offer_rooms SET updated_at = ? WHERE public_id = ?",
                    (now, room["public_id"]),
                )
        self.send_json(HTTPStatus.OK, {"ok": True, "node_id": node["node_public_id"]})

    def local_offer_room_payload(self, room: sqlite3.Row) -> dict:
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            nodes = db.execute(
                "SELECT node_public_id, card_id, device_label, status, result, created_at, updated_at "
                "FROM local_offer_nodes WHERE room_public_id = ? ORDER BY card_id",
                (room["public_id"],),
            ).fetchall()
        return {
            "schema_version": "0.1",
            "experiment_id": "E007",
            "checkpoint": "3B",
            "room_id": room["public_id"],
            "protocol_revision": room["protocol_revision"],
            "status": room["status"],
            "expected_nodes": room["expected_nodes"],
            "nodes": [{**dict(node), "result": json.loads(node["result"])} for node in nodes],
            "created_at": room["created_at"],
            "updated_at": room["updated_at"],
            "claim_boundary": "Local synthetic retrieval, policy states, and stored evidence transport only; no merge or final answer.",
        }

    def local_offer_status(self, body: object) -> None:
        if not isinstance(body, dict):
            raise ValueError("invalid local-offer status request")
        token = body.get("owner_token")
        if not isinstance(token, str) or len(token) > 200:
            raise ValueError("invalid owner token")
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            room = db.execute(
                "SELECT * FROM local_offer_rooms WHERE owner_token_hash = ?", (token_hash(token),)
            ).fetchone()
        if room is None:
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "local-offer room not found"})
            return
        self.send_json(HTTPStatus.OK, self.local_offer_room_payload(room))

    def publish_local_offer_room(self, body: object) -> None:
        if not isinstance(body, dict) or body.get("consent") is not True:
            raise ValueError("publication consent is required")
        token = body.get("owner_token")
        if not isinstance(token, str) or len(token) > 200:
            raise ValueError("invalid owner token")
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            room = db.execute(
                "SELECT * FROM local_offer_rooms WHERE owner_token_hash = ?", (token_hash(token),)
            ).fetchone()
            if room is None:
                self.send_json(HTTPStatus.NOT_FOUND, {"error": "local-offer room not found"})
                return
            if room["status"] != "complete":
                raise ValueError("all four local libraries must finish before publication")
            db.execute(
                "UPDATE local_offer_rooms SET public = 1, updated_at = ? WHERE public_id = ?",
                (utc_now(), room["public_id"]),
            )
        self.send_json(
            HTTPStatus.OK, {"ok": True, "public_path": f"/api/public/{room['public_id']}"}
        )

    def public_local_offer_rooms(self) -> list[dict]:
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            rooms = db.execute(
                "SELECT * FROM local_offer_rooms WHERE public = 1 ORDER BY row_id DESC"
            ).fetchall()
        return [self.local_offer_room_payload(room) for room in rooms]

    def get_public(self, public_id: str) -> None:
        public_id = public_id.upper()
        if public_id == "H0001":
            self.send_json(HTTPStatus.OK, MAIN_HYPOTHESIS, public=True)
            return
        if public_id == "E002":
            self.get_public_experiment()
            return
        if public_id == "E003":
            self.get_public_e003()
            return
        if re.fullmatch(r"A[0-9]{4,}", public_id):
            with sqlite3.connect(self.db_path) as db:
                db.row_factory = sqlite3.Row
                room = db.execute(
                    "SELECT * FROM attention_rooms WHERE public_id = ? AND public = 1",
                    (public_id,),
                ).fetchone()
            if room is None:
                self.send_json(HTTPStatus.NOT_FOUND, {"error": "attention run not found"})
                return
            self.send_json(HTTPStatus.OK, self.attention_room_payload(room), public=True, max_age=2)
            return
        if re.fullmatch(r"L[0-9]{4,}", public_id):
            with sqlite3.connect(self.db_path) as db:
                db.row_factory = sqlite3.Row
                room = db.execute(
                    "SELECT * FROM local_offer_rooms WHERE public_id = ? AND public = 1",
                    (public_id,),
                ).fetchone()
            if room is None:
                self.send_json(HTTPStatus.NOT_FOUND, {"error": "local-offer run not found"})
                return
            self.send_json(HTTPStatus.OK, self.local_offer_room_payload(room), public=True, max_age=2)
            return
        if public_id == "E004":
            self.get_public_e004()
            return
        if RUN_ID_RE.fullmatch(public_id):
            record = self.public_experiment_run(public_id)
            if record is None:
                self.send_json(HTTPStatus.NOT_FOUND, {"error": "run not found"})
                return
            self.send_json(HTTPStatus.OK, record, public=True, max_age=2)
            return
        if public_id.startswith("Q"):
            self.get_public_question(public_id)
            return
        if not PUBLIC_ID_RE.fullmatch(public_id) or not public_id.startswith("T"):
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "record not found"})
            return
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            record = db.execute(
                "SELECT public_id, door, payload, author, parent_public_id, relation, created_at, updated_at "
                "FROM contributions WHERE public_id = ? AND status = 'public'",
                (public_id,),
            ).fetchone()
        if record is None:
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "record not found"})
            return
        response = dict(record)
        response["payload"] = json.loads(response["payload"])
        response["status"] = "public"
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            children = db.execute(
                "SELECT public_id, payload, author FROM contributions "
                "WHERE parent_public_id = ? AND relation = 'continues' AND status = 'public' "
                "ORDER BY row_id",
                (public_id,),
            ).fetchall()
            questions = db.execute(
                "SELECT public_id, payload, author, research_status, created_at FROM questions "
                "WHERE source_trace_id = ? AND status = 'public' ORDER BY row_id",
                (public_id,),
            ).fetchall()
        response["continuations"] = [
            {
                "public_id": child["public_id"],
                "question": json.loads(child["payload"]).get("question", ""),
                "author": child["author"],
            }
            for child in children
        ]
        response["derived_questions"] = [
            {
                "public_id": question["public_id"],
                "question": json.loads(question["payload"]).get("question", ""),
                "needed": json.loads(question["payload"]).get("needed", ""),
                "author": question["author"],
                "status": question["research_status"],
                "created_at": question["created_at"],
            }
            for question in questions
        ]
        self.send_json(HTTPStatus.OK, response, public=True)

    def question_traces(self, public_id: str) -> list[dict]:
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute(
                "SELECT public_id, door, author, relation, created_at FROM contributions "
                "WHERE parent_public_id = ? AND relation = 'answers' AND status = 'public' "
                "ORDER BY row_id",
                (public_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def public_question_from_row(self, row: sqlite3.Row, traces: list[dict] | None = None) -> dict:
        record = dict(row)
        record["payload"] = json.loads(record["payload"])
        record["object_type"] = "question"
        record["status"] = record.pop("research_status")
        record["traces"] = traces if traces is not None else self.question_traces(record["public_id"])
        return record

    def get_public_question(self, public_id: str) -> None:
        if not re.fullmatch(r"Q[0-9]{4,}", public_id):
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "question not found"})
            return
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            row = db.execute(
                "SELECT public_id, payload, author, source_trace_id, source_event_id, relation, "
                "research_status, created_at, updated_at "
                "FROM questions WHERE public_id = ? AND status = 'public'",
                (public_id,),
            ).fetchone()
        if row is None:
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "question not found"})
            return
        self.send_json(HTTPStatus.OK, self.public_question_from_row(row), public=True)

    def public_questions(self) -> list[dict]:
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute(
                "SELECT public_id, payload, author, source_trace_id, source_event_id, relation, "
                "research_status, created_at, updated_at "
                "FROM questions WHERE status = 'public' ORDER BY row_id"
            ).fetchall()
            trace_rows = db.execute(
                "SELECT public_id, door, author, parent_public_id, relation, created_at "
                "FROM contributions WHERE relation = 'answers' AND status = 'public' "
                "ORDER BY row_id"
            ).fetchall()
        traces_by_question: dict[str, list[dict]] = defaultdict(list)
        for trace in trace_rows:
            value = dict(trace)
            parent_id = value.pop("parent_public_id")
            traces_by_question[parent_id].append(value)
        return [
            self.public_question_from_row(row, traces_by_question.get(row["public_id"], []))
            for row in rows
        ]

    def public_records(self) -> list[dict]:
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute(
                "SELECT public_id, door, payload, author, parent_public_id, relation, created_at, updated_at "
                "FROM contributions WHERE status = 'public' ORDER BY row_id"
            ).fetchall()
        records = []
        for row in rows:
            record = dict(row)
            record["payload"] = json.loads(record["payload"])
            record["status"] = "public"
            records.append(record)
        return records

    def public_events(self) -> list[dict]:
        with sqlite3.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute(
                "SELECT event_id, event_type, object_type, object_id, actor, links, payload, created_at "
                "FROM events ORDER BY row_id"
            ).fetchall()
            public_trace_ids = {
                row[0] for row in db.execute(
                    "SELECT public_id FROM contributions WHERE status = 'public'"
                )
            }
            public_question_ids = {
                row[0] for row in db.execute(
                    "SELECT public_id FROM questions WHERE status = 'public'"
                )
            }
        events = []
        for row in rows:
            event = dict(row)
            if event["object_type"] == "trace" and event["object_id"] not in public_trace_ids:
                continue
            if event["object_type"] == "question" and event["object_id"] not in public_question_ids:
                continue
            event["links"] = json.loads(event["links"])
            event["payload"] = json.loads(event["payload"])
            event["verified"] = False
            events.append(event)
        event_ids = {
            (event["object_type"], event["object_id"]): event["event_id"]
            for event in events
        }
        for event in events:
            for link in event["links"]:
                if "target_event_id" not in link:
                    target_event_id = event_ids.get((link.get("target_type"), link.get("target_id")))
                    if target_event_id:
                        link["target_event_id"] = target_event_id
        return events

    def public_corpus(self) -> dict:
        return {
            "schema_version": "0.2",
            "schema": "https://joinmultiplayer.ai/data/corpus-schema-v0.2.json",
            "license": "https://joinmultiplayer.ai/data-license/",
            "questions": self.public_questions(),
            "traces": self.public_records(),
            "events": self.public_events(),
        }

    def get_public_questions(self, output_format: str) -> None:
        questions = self.public_questions()
        if output_format == "jsonl":
            payload = b"".join(
                json.dumps(question, ensure_ascii=False).encode("utf-8") + b"\n"
                for question in questions
            )
            self.send_payload(
                HTTPStatus.OK, payload, "application/x-ndjson; charset=utf-8", public=True
            )
            return
        self.send_json(
            HTTPStatus.OK,
            {
                "schema_version": "0.2",
                "license": "https://joinmultiplayer.ai/data-license/",
                "questions": questions,
            },
            public=True,
        )

    def get_public_events(self, output_format: str) -> None:
        events = self.public_events()
        if output_format == "jsonl":
            payload = b"".join(
                json.dumps(event, ensure_ascii=False).encode("utf-8") + b"\n" for event in events
            )
            self.send_payload(HTTPStatus.OK, payload, "application/x-ndjson; charset=utf-8", public=True)
            return
        self.send_json(
            HTTPStatus.OK,
            {"schema_version": "0.1", "events": events},
            public=True,
        )

    def get_public_records(self, output_format: str) -> None:
        records = self.public_records()
        if output_format == "jsonl":
            payload = b"".join(
                json.dumps(record, ensure_ascii=False).encode("utf-8") + b"\n" for record in records
            )
            self.send_payload(HTTPStatus.OK, payload, "application/x-ndjson; charset=utf-8", public=True)
            return
        self.send_json(
            HTTPStatus.OK,
            {
                "schema_version": "0.2",
                "schema": "https://joinmultiplayer.ai/data/trace-schema-v0.2.json",
                "license": "https://joinmultiplayer.ai/data-license/",
                "records": records,
            },
            public=True,
        )

    def send_json(
        self,
        status: HTTPStatus,
        value: object,
        *,
        public: bool = False,
        max_age: int | None = None,
    ) -> None:
        payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_payload(
            status,
            payload,
            "application/json; charset=utf-8",
            public=public,
            max_age=max_age,
        )

    def send_payload(
        self,
        status: HTTPStatus,
        payload: bytes,
        content_type: str,
        *,
        public: bool = False,
        max_age: int | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        cache_age = 60 if max_age is None else max(0, max_age)
        self.send_header("Cache-Control", f"public, max-age={cache_age}" if public else "no-store")
        if public:
            self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8091)
    args = parser.parse_args()

    init_db(args.db)
    ApplicationHandler.db_path = args.db
    handler = lambda *handler_args, **kwargs: ApplicationHandler(  # noqa: E731
        *handler_args, directory=str(args.site), **kwargs
    )
    server = ThreadingHTTPServer((args.host, args.port), handler)
    server.serve_forever()


if __name__ == "__main__":
    main()

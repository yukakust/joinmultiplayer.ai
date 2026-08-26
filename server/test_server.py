import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from http import HTTPStatus
from pathlib import Path

from server import (
    ApplicationHandler,
    RateLimiter,
    init_db,
    new_physical_table,
    physical_tasks,
    record_publication_event,
    record_question_publication_event,
    token_hash,
    validate_run_event,
    validate_question_submission,
    validate_submission,
)


NOW = "2026-08-19T00:00:00+00:00"


def insert_trace(db, public_id="T0001", *, status="public", question="What changed?"):
    payload = json.dumps(
        {"question": question, "responses": [{"model": "Example AI", "raw": "This."}]}
    )
    db.execute(
        "INSERT INTO contributions "
        "(public_id, token_hash, door, payload, author, status, created_at, updated_at) "
        "VALUES (?, ?, 'd04', ?, 'anonymous', ?, ?, ?)",
        (public_id, f"hash-{public_id}", payload, status, NOW, NOW),
    )


def insert_question(
    db,
    public_id="Q0001",
    *,
    status="public",
    source_trace_id="T0001",
    source_event_id="",
    question="What do repeated attempts add?",
):
    payload = json.dumps(
        {
            "question": question,
            "why_it_matters": "It separates repetition from independent intelligence.",
            "starting_point": "Repeated samples can expose instability.",
            "sources": "SelfCheckGPT",
            "needed": "A controlled comparison under one budget.",
            "next_move": "answer",
            "language": "en",
        }
    )
    db.execute(
        "INSERT INTO questions "
        "(public_id, token_hash, payload, author, source_trace_id, source_event_id, "
        "status, created_at, updated_at) VALUES (?, ?, ?, 'anonymous', ?, ?, ?, ?, ?)",
        (public_id, f"hash-{public_id}", payload, source_trace_id, source_event_id, status, NOW, NOW),
    )


def handler_for(path):
    handler = object.__new__(ApplicationHandler)
    handler.db_path = path
    handler.limiter = RateLimiter()
    handler.client_key = lambda: "test-client"
    handler.sent = None

    def capture(status, value, **kwargs):
        handler.sent = (status, value, kwargs)

    handler.send_json = capture
    return handler


class SubmissionTests(unittest.TestCase):
    def question_body(self, **overrides):
        body = {
            "question": "What do repeated attempts add?",
            "why_it_matters": "It separates repetition from independent intelligence.",
            "starting_point": "Repeated samples can expose instability.",
            "sources": "SelfCheckGPT",
            "needed": "A controlled comparison under one budget.",
            "next_move": "answer",
            "language": "en",
            "source_trace_id": "T0001",
            "author_mode": "anonymous",
            "consent": True,
        }
        body.update(overrides)
        return body

    def test_d04_minimum(self):
        door, payload, author = validate_submission(
            {
                "door": "d04",
                "question": "Why?",
                "responses": [{"model": "Example AI", "raw": "Because."}],
                "author_mode": "anonymous",
                "consent": True,
            }
        )
        self.assertEqual(door, "d04")
        self.assertEqual(author, "anonymous")
        self.assertEqual(len(payload["responses"]), 1)
        self.assertEqual(payload["responses"][0]["run_at"], "unknown")

    def test_d06_requires_expert_observation(self):
        with self.assertRaises(ValueError):
            validate_submission(
                {
                    "door": "d06",
                    "question": "Is this correct?",
                    "responses": [{"model": "Example AI", "raw": "Yes."}],
                    "consent": True,
                }
            )

    def test_consent_is_required(self):
        with self.assertRaises(ValueError):
            validate_submission(
                {
                    "door": "d04",
                    "question": "Why?",
                    "responses": [{"model": "Example AI", "raw": "Because."}],
                }
            )

    def test_question_submission_contract(self):
        payload, author, source_trace_id = validate_question_submission(self.question_body())
        self.assertEqual(author, "anonymous")
        self.assertEqual(source_trace_id, "T0001")
        self.assertEqual(payload["next_move"], "answer")
        self.assertEqual(payload["needed"], "A controlled comparison under one budget.")

    def test_question_requires_why_needed_and_consent(self):
        for field, value in (
            ("why_it_matters", ""),
            ("needed", ""),
            ("consent", False),
        ):
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_question_submission(self.question_body(**{field: value}))

    def test_question_rejects_invalid_next_move_and_source_id(self):
        with self.assertRaises(ValueError):
            validate_question_submission(self.question_body(next_move="vote"))
        with self.assertRaises(ValueError):
            validate_question_submission(self.question_body(next_move="experiment"))
        with self.assertRaises(ValueError):
            validate_question_submission(self.question_body(source_trace_id="Q0001"))

    def test_database_initializes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.sqlite3"
            init_db(path)
            self.assertTrue(path.exists())
            with sqlite3.connect(path) as db:
                columns = {row[1] for row in db.execute("PRAGMA table_info(contributions)")}
                self.assertIn("parent_public_id", columns)
                self.assertIsNotNone(db.execute("SELECT name FROM sqlite_master WHERE name = 'events'").fetchone())
                question_columns = {row[1] for row in db.execute("PRAGMA table_info(questions)")}
                self.assertIn("research_status", question_columns)
                self.assertIsNotNone(
                    db.execute(
                        "SELECT name FROM sqlite_master WHERE name = 'physical_rooms'"
                    ).fetchone()
                )
                self.assertIsNotNone(
                    db.execute(
                        "SELECT name FROM sqlite_master WHERE name = 'attention_rooms'"
                    ).fetchone()
                )
                self.assertIsNotNone(
                    db.execute(
                        "SELECT name FROM sqlite_master WHERE name = 'local_offer_rooms'"
                    ).fetchone()
                )

    def test_attention_room_four_node_private_then_public_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.sqlite3"
            init_db(path)
            handler = handler_for(path)
            question = "Не могу решить CV-задачу с маленькими объектами."
            handler.create_attention_room(
                {"question": question, "author_mode": "pseudonym", "pseudonym": "Morrow", "consent": True}
            )
            self.assertEqual(handler.sent[0], HTTPStatus.CREATED)
            room_id = handler.sent[1]["room_id"]
            owner_token = handler.sent[1]["owner_token"]
            join_token = handler.sent[1]["join_token"]
            question_hash = hashlib.sha256(question.encode()).hexdigest()
            self.assertEqual(handler.sent[1]["question_hash"], question_hash)

            cards = (
                ("ATT-Y1", "yukabox", 0.8, 0.3),
                ("ATT-Y2", "yukabox", 0.1, 0.0),
                ("ATT-M1", "owner-macbook", 0.7, 0.2),
                ("ATT-M2", "owner-macbook", 0.05, 0.0),
            )
            for card_id, device, vector, exact in cards:
                handler.join_attention_room(
                    {"join_token": join_token, "card_id": card_id, "device_label": device}
                )
                self.assertEqual(handler.sent[0], HTTPStatus.CREATED)
                node_token = handler.sent[1]["node_token"]
                self.assertEqual(handler.sent[1]["question"], question)
                handler.respond_attention_node(
                    {
                        "node_token": node_token,
                        "question_hash": question_hash,
                        "whole_text_vector": vector,
                        "exact_terms": exact,
                        "matched_terms": ["cv"] if exact else [],
                        "latency_ms": 4.2,
                        "client_version": "test-v0.1",
                    }
                )
                self.assertEqual(handler.sent[0], HTTPStatus.OK)

            handler.attention_status({"owner_token": owner_token})
            self.assertEqual(handler.sent[1]["status"], "complete")
            self.assertEqual(len(handler.sent[1]["nodes"]), 4)
            self.assertEqual({node["device_label"] for node in handler.sent[1]["nodes"]}, {"yukabox", "owner-macbook"})

            self.assertEqual(handler.public_attention_rooms(), [])
            handler.publish_attention_room({"owner_token": owner_token, "consent": True})
            self.assertEqual(handler.sent[0], HTTPStatus.OK)
            public = handler.public_attention_rooms()
            self.assertEqual(public[0]["room_id"], room_id)
            self.assertNotIn("owner_token", public[0])
            self.assertNotIn("join_token", public[0])

    def test_attention_rejects_changed_question_and_wrong_device(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.sqlite3"
            init_db(path)
            handler = handler_for(path)
            handler.create_attention_room(
                {"question": "Exact question", "author_mode": "anonymous", "consent": True}
            )
            join_token = handler.sent[1]["join_token"]
            with self.assertRaisesRegex(ValueError, "another declared device"):
                handler.join_attention_room(
                    {"join_token": join_token, "card_id": "ATT-Y1", "device_label": "owner-macbook"}
                )
            handler.join_attention_room(
                {"join_token": join_token, "card_id": "ATT-Y1", "device_label": "yukabox"}
            )
            node_token = handler.sent[1]["node_token"]
            with self.assertRaisesRegex(ValueError, "changed in transit"):
                handler.respond_attention_node(
                    {
                        "node_token": node_token,
                        "question_hash": "wrong",
                        "whole_text_vector": 0.1,
                        "exact_terms": 0.1,
                        "matched_terms": [],
                        "latency_ms": 1,
                        "client_version": "test",
                    }
                )

    def test_public_corpus_excludes_pending_records(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.sqlite3"
            init_db(path)
            payload = json.dumps(
                {"question": "What changed?", "responses": [{"model": "Example AI", "raw": "This."}]}
            )
            with sqlite3.connect(path) as db:
                values = ("hash", "d04", payload, "anonymous", "2026-08-19T00:00:00+00:00", "2026-08-19T00:00:00+00:00")
                cursor = db.execute(
                    "INSERT INTO contributions (token_hash, door, payload, author, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    values,
                )
                db.execute("UPDATE contributions SET public_id = 'T0001' WHERE row_id = ?", (cursor.lastrowid,))
                cursor = db.execute(
                    "INSERT INTO contributions (token_hash, door, payload, author, status, created_at, updated_at) VALUES (?, ?, ?, ?, 'public', ?, ?)",
                    ("hash2", "d04", payload, "Yuka", values[-2], values[-1]),
                )
                db.execute("UPDATE contributions SET public_id = 'T0002' WHERE row_id = ?", (cursor.lastrowid,))
            handler = object.__new__(ApplicationHandler)
            handler.db_path = path
            records = handler.public_records()
            self.assertEqual([record["public_id"] for record in records], ["T0002"])
            self.assertEqual(records[0]["payload"]["question"], "What changed?")

    def test_continuation_creates_a_linked_global_event(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.sqlite3"
            init_db(path)
            payload = json.dumps(
                {"question": "Who notices the gap?", "responses": [{"model": "Example AI", "raw": "A person."}]}
            )
            with sqlite3.connect(path) as db:
                db.execute(
                    "INSERT INTO contributions "
                    "(public_id, token_hash, door, payload, author, status, parent_public_id, relation, created_at, updated_at) "
                    "VALUES ('T0002', 'child', 'd04', ?, 'Yuka', 'public', 'T0001', 'continues', ?, ?)",
                    (payload, "2026-08-19T00:00:00+00:00", "2026-08-19T00:00:00+00:00"),
                )
                record_publication_event(db, "T0002")
            handler = object.__new__(ApplicationHandler)
            handler.db_path = path
            events = handler.public_events()
            self.assertEqual(events[0]["event_id"], "E000001")
            self.assertEqual(events[0]["event_type"], "trace_continued")
            self.assertEqual(events[0]["links"][0]["target_id"], "T0001")

    def test_pending_questions_are_excluded_from_public_questions_and_corpus(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.sqlite3"
            init_db(path)
            with sqlite3.connect(path) as db:
                insert_trace(db, "T0001", status="public")
                insert_question(db, "Q0001", status="pending")
                insert_question(db, "Q0002", status="public")
            handler = handler_for(path)
            questions = handler.public_questions()
            corpus = handler.public_corpus()
            self.assertEqual([question["public_id"] for question in questions], ["Q0002"])
            self.assertEqual([question["public_id"] for question in corpus["questions"]], ["Q0002"])
            self.assertEqual(
                corpus["schema"], "https://joinmultiplayer.ai/data/corpus-schema-v0.2.json"
            )
            self.assertEqual(questions[0]["status"], "open")
            self.assertNotIn("moderation_status", questions[0])

    def test_trace_feed_declares_schema_that_accepts_question_answers(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.sqlite3"
            init_db(path)
            with sqlite3.connect(path) as db:
                insert_trace(db)
                insert_question(db)
                payload = json.dumps(
                    {
                        "question": "What do repeated attempts add?",
                        "responses": [{"model": "Example AI", "raw": "A signal."}],
                    }
                )
                db.execute(
                    "INSERT INTO contributions "
                    "(public_id, token_hash, door, payload, author, status, parent_public_id, relation, created_at, updated_at) "
                    "VALUES ('T0002', 'answer', 'd04', ?, 'anonymous', 'public', 'Q0001', 'answers', ?, ?)",
                    (payload, NOW, NOW),
                )
            handler = handler_for(path)
            handler.get_public_records("json")
            response = handler.sent[1]
            self.assertEqual(response["schema_version"], "0.2")
            self.assertEqual(
                response["schema"],
                "https://joinmultiplayer.ai/data/trace-schema-v0.2.json",
            )
            self.assertEqual(response["records"][1]["relation"], "answers")

    def test_question_publication_creates_one_linked_global_event(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.sqlite3"
            init_db(path)
            with sqlite3.connect(path) as db:
                insert_trace(db)
                record_publication_event(db, "T0001")
                source_event_id = db.execute(
                    "SELECT event_id FROM events WHERE object_id = 'T0001'"
                ).fetchone()[0]
                insert_question(db, source_event_id=source_event_id)
                record_question_publication_event(db, "Q0001")
                record_question_publication_event(db, "Q0001")
                count = db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            handler = handler_for(path)
            events = handler.public_events()
            self.assertEqual(count, 2)
            self.assertEqual(events[1]["event_id"], "E000002")
            self.assertEqual(events[1]["event_type"], "question_opened")
            self.assertEqual(events[1]["object_type"], "question")
            self.assertEqual(events[1]["payload"]["next_move"], "answer")
            self.assertEqual(
                events[1]["payload"]["needed"], "A controlled comparison under one budget."
            )
            self.assertEqual(events[1]["links"][0]["target_id"], "T0001")
            self.assertEqual(events[1]["links"][0]["target_event_id"], "E000001")

    def test_moderation_cli_publishes_a_question_and_its_event(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.sqlite3"
            init_db(path)
            with sqlite3.connect(path) as db:
                insert_trace(db)
                record_publication_event(db, "T0001")
                insert_question(db, status="pending", source_event_id="E000001")
            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).with_name("moderate.py")),
                    "--db",
                    str(path),
                    "status",
                    "Q0001",
                    "public",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn("Q0001: public", result.stdout)
            with sqlite3.connect(path) as db:
                status = db.execute(
                    "SELECT status FROM questions WHERE public_id = 'Q0001'"
                ).fetchone()[0]
                event_type = db.execute(
                    "SELECT event_type FROM events WHERE object_id = 'Q0001'"
                ).fetchone()[0]
            self.assertEqual(status, "public")
            self.assertEqual(event_type, "question_opened")

    def test_create_question_uses_public_source_and_keeps_token_private(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.sqlite3"
            init_db(path)
            with sqlite3.connect(path) as db:
                insert_trace(db)
                record_publication_event(db, "T0001")
            handler = handler_for(path)
            handler.create_question(self.question_body())
            status, response, _ = handler.sent
            self.assertEqual(status, HTTPStatus.CREATED)
            self.assertEqual(response["id"], "Q0001")
            self.assertEqual(response["status_path"], f"/question-submission/#{response['token']}")
            with sqlite3.connect(path) as db:
                row = db.execute(
                    "SELECT token_hash, status, source_event_id FROM questions WHERE public_id = 'Q0001'"
                ).fetchone()
            self.assertEqual(row[0], token_hash(response["token"]))
            self.assertNotEqual(row[0], response["token"])
            self.assertEqual(row[1], "pending")
            self.assertEqual(row[2], "E000001")
            self.assertEqual(handler.public_questions(), [])

    def test_question_cannot_derive_from_a_private_trace(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.sqlite3"
            init_db(path)
            with sqlite3.connect(path) as db:
                insert_trace(db, status="pending")
            handler = handler_for(path)
            with self.assertRaisesRegex(ValueError, "source trace is unavailable"):
                handler.create_question(self.question_body())
            with sqlite3.connect(path) as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM questions").fetchone()[0], 0)

    def test_question_private_status_and_public_detail_have_distinct_statuses(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.sqlite3"
            init_db(path)
            with sqlite3.connect(path) as db:
                insert_trace(db)
                record_publication_event(db, "T0001")
            handler = handler_for(path)
            handler.create_question(self.question_body())
            token = handler.sent[1]["token"]
            handler.get_question_status({"token": token})
            private = handler.sent[1]
            self.assertEqual(private["status"], "pending")
            self.assertEqual(private["research_status"], "open")
            self.assertNotIn("public_path", private)

            with sqlite3.connect(path) as db:
                db.execute("UPDATE questions SET status = 'public' WHERE public_id = 'Q0001'")
                record_question_publication_event(db, "Q0001")
            handler.get_question_status({"token": token})
            self.assertEqual(handler.sent[1]["status"], "public")
            self.assertEqual(handler.sent[1]["public_path"], "/question/?id=Q0001")

            handler.get_public("Q0001")
            public = handler.sent[1]
            self.assertEqual(public["status"], "open")
            self.assertNotIn("review_note", public)
            self.assertEqual(public["payload"]["question"], "What do repeated attempts add?")
            self.assertTrue(handler.sent[2]["public"])

    def test_source_trace_lists_its_public_derived_questions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.sqlite3"
            init_db(path)
            with sqlite3.connect(path) as db:
                insert_trace(db)
                insert_question(db)
                insert_question(db, public_id="Q0002", status="pending", question="Private question")
            handler = handler_for(path)
            handler.get_public("T0001")
            questions = handler.sent[1]["derived_questions"]
            self.assertEqual(len(questions), 1)
            self.assertEqual(questions[0]["public_id"], "Q0001")
            self.assertEqual(questions[0]["status"], "open")
            self.assertEqual(questions[0]["question"], "What do repeated attempts add?")

    def test_trace_can_answer_public_question_with_exact_wording(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.sqlite3"
            init_db(path)
            with sqlite3.connect(path) as db:
                insert_trace(db)
                record_publication_event(db, "T0001")
                insert_question(db)
                record_question_publication_event(db, "Q0001")
            handler = handler_for(path)
            handler.create_contribution(
                {
                    "door": "d04",
                    "question": "What do repeated attempts add?",
                    "responses": [{"model": "Example AI", "raw": "A confidence signal."}],
                    "parent_id": "Q0001",
                    "relation": "answers",
                    "consent": True,
                }
            )
            self.assertEqual(handler.sent[0], HTTPStatus.CREATED)
            trace_id = handler.sent[1]["id"]
            with sqlite3.connect(path) as db:
                db.row_factory = sqlite3.Row
                trace = db.execute(
                    "SELECT parent_public_id, relation, payload FROM contributions WHERE public_id = ?",
                    (trace_id,),
                ).fetchone()
                self.assertEqual(trace["parent_public_id"], "Q0001")
                self.assertEqual(trace["relation"], "answers")
                self.assertEqual(json.loads(trace["payload"])["question_id"], "Q0001")
                db.execute(
                    "UPDATE contributions SET status = 'public' WHERE public_id = ?", (trace_id,)
                )
                record_publication_event(db, trace_id)
            answer_event = handler.public_events()[-1]
            self.assertEqual(answer_event["event_type"], "trace_answered")
            self.assertEqual(answer_event["links"][0]["relation"], "answers")
            self.assertEqual(answer_event["links"][0]["target_id"], "Q0001")
            self.assertEqual(answer_event["links"][0]["target_event_id"], "E000002")
            with sqlite3.connect(path) as db:
                research_status = db.execute(
                    "SELECT research_status FROM questions WHERE public_id = 'Q0001'"
                ).fetchone()[0]
            self.assertEqual(research_status, "open")

    def test_local_offer_four_node_private_then_public_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.sqlite3"
            init_db(path)
            handler = handler_for(path)
            handler.create_local_offer_room(
                {"author_mode": "pseudonym", "pseudonym": "Morrow", "consent": True}
            )
            self.assertEqual(handler.sent[0], HTTPStatus.CREATED)
            room_id = handler.sent[1]["room_id"]
            owner_token = handler.sent[1]["owner_token"]
            join_token = handler.sent[1]["join_token"]

            cards = (
                ("ATT-Y1", "yukabox"),
                ("ATT-Y2", "yukabox"),
                ("ATT-M1", "owner-macbook"),
                ("ATT-M2", "owner-macbook"),
            )
            for card_id, device in cards:
                handler.join_local_offer_room(
                    {"join_token": join_token, "card_id": card_id, "device_label": device}
                )
                self.assertEqual(handler.sent[0], HTTPStatus.CREATED)
                joined = handler.sent[1]
                results = []
                for question in joined["questions"]:
                    for lane in ("exact_terms", "chargram_vector", "multilingual_neural"):
                        item = {
                            "question_id": question["id"],
                            "question_hash": question["question_hash"],
                            "lane": lane,
                            "status": "empty",
                            "score": 0.1,
                            "source_id": f"{card_id}-NOISE",
                            "capsule": None,
                            "canary_hash": "",
                        }
                        if card_id == "ATT-Y1" and question["id"] == "K01" and lane == "exact_terms":
                            item.update(
                                {
                                    "status": "found",
                                    "score": 0.9,
                                    "source_id": "Y1-CV-01",
                                    "capsule": {
                                        "claim": "Overlapping tiles can help.",
                                        "evidence": "The exact local evidence text.",
                                        "source": "local experiment",
                                        "source_lineage": "cv-field-exp-017",
                                        "conditions": "tiny objects",
                                        "limitations": "one dataset",
                                        "permission": "share_this_capsule",
                                    },
                                }
                            )
                        results.append(item)
                handler.contribute_local_offer_node(
                    {
                        "node_token": joined["node_token"],
                        "client_version": "test-v0.1",
                        "runtime": "test-runtime",
                        "memory_revision": "e007-local-memory-v0.1",
                        "model": "test-search-model",
                        "model_revision": "test-revision",
                        "lane_config": {
                            lane: {"threshold": 0.5, "calibration_f1": 1.0}
                            for lane in ("exact_terms", "chargram_vector", "multilingual_neural")
                        },
                        "results": results,
                    }
                )
                self.assertEqual(handler.sent[0], HTTPStatus.OK)

            handler.local_offer_status({"owner_token": owner_token})
            self.assertEqual(handler.sent[1]["status"], "complete")
            self.assertEqual(len(handler.sent[1]["nodes"]), 4)
            self.assertEqual(handler.public_local_offer_rooms(), [])

            handler.publish_local_offer_room({"owner_token": owner_token, "consent": True})
            self.assertEqual(handler.sent[0], HTTPStatus.OK)
            public = handler.public_local_offer_rooms()
            self.assertEqual(public[0]["room_id"], room_id)
            self.assertNotIn("owner_token", public[0])
            self.assertNotIn("join_token", public[0])
            encoded = json.dumps(public[0], ensure_ascii=False)
            self.assertNotIn(join_token, encoded)
            self.assertNotIn(owner_token, encoded)

    def test_local_offer_rejects_changed_question_and_capsule_on_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.sqlite3"
            init_db(path)
            handler = handler_for(path)
            handler.create_local_offer_room(
                {"author_mode": "anonymous", "consent": True}
            )
            join_token = handler.sent[1]["join_token"]
            handler.join_local_offer_room(
                {"join_token": join_token, "card_id": "ATT-Y1", "device_label": "yukabox"}
            )
            questions = handler.sent[1]["questions"]
            node_token = handler.sent[1]["node_token"]
            results = []
            for question in questions:
                for lane in ("exact_terms", "chargram_vector", "multilingual_neural"):
                    results.append(
                        {
                            "question_id": question["id"],
                            "question_hash": question["question_hash"],
                            "lane": lane,
                            "status": "empty",
                            "score": 0.0,
                            "source_id": "Y1-CV-06",
                            "capsule": None,
                            "canary_hash": "",
                        }
                    )
            base = {
                "node_token": node_token,
                "client_version": "test-v0.1",
                "runtime": "test-runtime",
                "memory_revision": "e007-local-memory-v0.1",
                "model": "test-search-model",
                "model_revision": "test-revision",
                "lane_config": {
                    lane: {"threshold": 0.5, "calibration_f1": 1.0}
                    for lane in ("exact_terms", "chargram_vector", "multilingual_neural")
                },
                "results": results,
            }
            changed = json.loads(json.dumps(base))
            changed["results"][0]["question_hash"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "changed in transit"):
                handler.contribute_local_offer_node(changed)

            leaked_capsule = json.loads(json.dumps(base))
            leaked_capsule["results"][0]["capsule"] = {"claim": "must not travel"}
            with self.assertRaisesRegex(ValueError, "only found"):
                handler.contribute_local_offer_node(leaked_capsule)

    def test_local_offer_can_rejoin_an_incomplete_slot_after_local_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.sqlite3"
            init_db(path)
            handler = handler_for(path)
            handler.create_local_offer_room({"author_mode": "anonymous", "consent": True})
            join_token = handler.sent[1]["join_token"]
            request = {"join_token": join_token, "card_id": "ATT-Y1", "device_label": "yukabox"}
            handler.join_local_offer_room(request)
            first = handler.sent[1]
            handler.join_local_offer_room(request)
            second = handler.sent[1]
            self.assertEqual(first["node_id"], second["node_id"])
            self.assertNotEqual(first["node_token"], second["node_token"])
            with sqlite3.connect(path) as db:
                self.assertEqual(
                    db.execute("SELECT COUNT(*) FROM local_offer_nodes").fetchone()[0], 1
                )

    def test_trace_cannot_change_public_question_wording(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.sqlite3"
            init_db(path)
            with sqlite3.connect(path) as db:
                insert_trace(db)
                insert_question(db)
            handler = handler_for(path)
            with self.assertRaisesRegex(ValueError, "match the public question exactly"):
                handler.create_contribution(
                    {
                        "door": "d04",
                        "question": "A different question",
                        "responses": [{"model": "Example AI", "raw": "An answer."}],
                        "parent_id": "Q0001",
                        "relation": "answers",
                        "consent": True,
                    }
                )

    def test_withdrawn_object_payload_is_removed_from_public_events(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.sqlite3"
            init_db(path)
            with sqlite3.connect(path) as db:
                insert_trace(db)
                record_publication_event(db, "T0001")
                db.execute("UPDATE contributions SET status = 'withdrawn' WHERE public_id = 'T0001'")
            handler = handler_for(path)
            self.assertEqual(handler.public_events(), [])

    def test_moderation_rejects_trace_when_parent_question_is_not_public(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.sqlite3"
            init_db(path)
            with sqlite3.connect(path) as db:
                insert_trace(db)
                insert_question(db, status="withdrawn")
                payload = json.dumps(
                    {
                        "question": "What do repeated attempts add?",
                        "responses": [{"model": "Example AI", "raw": "A signal."}],
                    }
                )
                db.execute(
                    "INSERT INTO contributions "
                    "(public_id, token_hash, door, payload, author, status, parent_public_id, relation, created_at, updated_at) "
                    "VALUES ('T0002', 'answer', 'd04', ?, 'anonymous', 'pending', 'Q0001', 'answers', ?, ?)",
                    (payload, NOW, NOW),
                )
            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).with_name("moderate.py")),
                    "--db",
                    str(path),
                    "status",
                    "T0002",
                    "public",
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("parent record is not public", result.stderr)
            with sqlite3.connect(path) as db:
                status = db.execute(
                    "SELECT status FROM contributions WHERE public_id = 'T0002'"
                ).fetchone()[0]
            self.assertEqual(status, "pending")

    def test_experiment_run_live_journal_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.sqlite3"
            init_db(path)
            handler = handler_for(path)
            handler.create_experiment_run(
                {
                    "experiment_id": "E002",
                    "agent": "codex",
                    "author_mode": "anonymous",
                    "consent": True,
                }
            )
            self.assertEqual(handler.sent[0], HTTPStatus.CREATED)
            run_id = handler.sent[1]["id"]
            token = handler.sent[1]["token"]
            self.assertTrue(run_id.startswith("R"))

            handler.append_experiment_run_event(
                {
                    "token": token,
                    "sequence": 1,
                    "event_type": "run_started",
                    "payload": {"model": "gpt-test", "client_version": "test"},
                }
            )
            handler.append_experiment_run_event(
                {
                    "token": token,
                    "sequence": 2,
                    "event_type": "agent_message",
                    "payload": {"text": "I will implement the falsification controls."},
                }
            )
            public = handler.public_experiment_run(run_id)
            self.assertEqual(public["status"], "running")
            self.assertEqual([event["sequence"] for event in public["events"]], [1, 2])
            self.assertNotIn("token", public)

            handler.append_experiment_run_event(
                {
                    "token": token,
                    "sequence": 3,
                    "event_type": "run_completed",
                    "payload": {"status": "completed", "summary": "Design complete."},
                }
            )
            self.assertEqual(handler.public_experiment_run(run_id)["status"], "completed")

    def test_public_journal_rejects_secrets_and_redacts_local_paths(self):
        with self.assertRaisesRegex(ValueError, "possible secret"):
            validate_run_event(
                {
                    "token": "run-token",
                    "sequence": 1,
                    "event_type": "agent_message",
                    "payload": {"text": "authorization: Bearer very-secret-value"},
                }
            )
        _, _, _, payload = validate_run_event(
            {
                "token": "run-token",
                "sequence": 1,
                "event_type": "agent_message",
                "payload": {"text": "Read /home/alice/public-repo/PROTOCOL.md"},
            }
        )
        self.assertEqual(payload["text"], "Read <local-path>")
        _, _, _, payload = validate_run_event(
            {
                "token": "run-token",
                "sequence": 2,
                "event_type": "agent_message",
                "payload": {"text": "See [artifact](/home/alice/public/microscope.html)."},
            }
        )
        self.assertEqual(payload["text"], "See [artifact](<local-path>).")

    def test_experiment_run_events_are_idempotent_but_not_replaceable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.sqlite3"
            init_db(path)
            handler = handler_for(path)
            handler.create_experiment_run(
                {"experiment_id": "E002", "agent": "codex", "consent": True}
            )
            token = handler.sent[1]["token"]
            event = {
                "token": token,
                "sequence": 1,
                "event_type": "checkpoint",
                "payload": {"text": "Protocol read."},
            }
            handler.append_experiment_run_event(event)
            handler.append_experiment_run_event(event)
            self.assertTrue(handler.sent[1]["duplicate"])
            changed = {**event, "payload": {"text": "Different event."}}
            with self.assertRaisesRegex(ValueError, "already exists"):
                handler.append_experiment_run_event(changed)

    def test_e002_public_record_includes_live_runs(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.sqlite3"
            init_db(path)
            handler = handler_for(path)
            handler.create_experiment_run(
                {"experiment_id": "E002", "agent": "codex", "consent": True}
            )
            handler.get_public_experiment()
            self.assertEqual(handler.sent[0], HTTPStatus.OK)
            self.assertEqual(handler.sent[1]["hypothesis"]["public_id"], "H0001")
            self.assertEqual(len(handler.sent[1]["runs"]), 1)
            self.assertEqual(handler.sent[1]["protocol_version"], "E002-draft-v0.4")
            self.assertEqual(
                handler.sent[1]["development_run"]["status"],
                "draft_gates_passed_not_a_result",
            )

    def test_e003_accepts_same_task_codex_journal_without_changing_claim_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.sqlite3"
            init_db(path)
            handler = handler_for(path)
            handler.create_experiment_run(
                {"experiment_id": "E003", "agent": "codex", "consent": True}
            )
            token = handler.sent[1]["token"]
            handler.get_experiment_run_status({"token": token})
            self.assertEqual(handler.sent[1]["experiment_id"], "E003")
            self.assertEqual(handler.sent[1]["protocol_version"], "E003-draft-v0.1")
            self.assertIn("not yet a language model", handler.sent[1]["task_prompt"])

    def test_e004_public_record_runs_authorized_development_arena(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.sqlite3"
            init_db(path)
            handler = handler_for(path)
            handler.get_public("E004")
            self.assertEqual(handler.sent[0], HTTPStatus.OK)
            experiment = handler.sent[1]
            self.assertEqual(experiment["status"], "arena_development_running")
            self.assertEqual(experiment["method"], "architecture_arena")
            self.assertEqual(experiment["protocol_version"], "E004-architecture-arena-v0.3")
            self.assertEqual(experiment["checkpoint"]["number"], 2)
            self.assertIn("what changed", experiment["visibility_rule"]["en"])
            self.assertIn("На каждом значимом этапе", experiment["visibility_rule"]["ru"])
            self.assertEqual(len(experiment["pockets"]), 9)
            self.assertEqual(experiment["pockets"][-1]["id"], "I09")
            self.assertTrue(all(item["status"] == "not_generated" for item in experiment["pockets"]))
            self.assertEqual(len(experiment["architectures"]), 4)
            self.assertTrue(all(item["status"] == "planned_not_run" for item in experiment["architectures"]))
            self.assertEqual(len(experiment["local_learning"]), 5)
            self.assertNotIn("dora_assembly", {item["id"] for item in experiment["architectures"]})
            self.assertEqual(experiment["checkpoint_artifact"], "/experiments/E004/checkpoint-1-v0.2.json")
            self.assertEqual(experiment["review_checkpoint_artifact"], "/experiments/E004/checkpoint-2.json")
            self.assertEqual(experiment["arena_progress_artifact"], "/experiments/E004/arena-progress.json")
            self.assertEqual(
                experiment["development_progress_artifact"],
                "/experiments/E004/development-progress.json",
            )
            self.assertIn("remain untested", experiment["claim_boundary"]["en"])

    def test_e004_artifact_schema_is_public_json_schema(self):
        schema_path = (
            Path(__file__).resolve().parents[1]
            / "site"
            / "experiments"
            / "E004"
            / "artifact-schema-v0.2.json"
        )
        schema = json.loads(schema_path.read_text())
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(schema["properties"]["experiment_id"]["const"], "E004")
        self.assertEqual(schema["properties"]["checkpoint"]["const"], 1)
        self.assertEqual(schema["properties"]["schema_version"]["const"], "0.2")

    def test_e004_checkpoint_links_live_candidates_and_verified_public_data(self):
        root = Path(__file__).resolve().parents[1] / "site" / "experiments" / "E004"
        checkpoint = json.loads((root / "checkpoint-1-v0.2.json").read_text())
        data_world = json.loads((root / "sample-tasks.json").read_text())
        self.assertEqual(len(checkpoint["architecture_candidates"]), 4)
        self.assertEqual(len(checkpoint["local_learning_candidates"]), 5)
        self.assertNotIn(
            "dora_assembly", {item["id"] for item in checkpoint["architecture_candidates"]}
        )
        rag = next(item for item in checkpoint["architecture_candidates"] if item["id"] == "rag_swarm")
        self.assertIn("Raw private records never leave", rag["description"]["en"])
        self.assertEqual(len(checkpoint["population"]["final_ids"]), 8)
        self.assertEqual(checkpoint["population"]["post_freeze_plugin_id"], "I09")
        self.assertEqual(len(data_world["books"]), 8)
        self.assertEqual(len(data_world["tasks"]), 12)
        for item in checkpoint["files"]:
            path = root / Path(item["path"]).name
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), item["sha256"])

    def test_three_physical_devices_train_compose_and_publish(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.sqlite3"
            init_db(path)
            handler = handler_for(path)
            handler.create_physical_room(
                {"author_mode": "pseudonym", "pseudonym": "Morrow", "consent": True}
            )
            self.assertEqual(handler.sent[0], HTTPStatus.CREATED)
            room = handler.sent[1]
            owner_token = room["owner_token"]
            node_tokens = []
            for label in ("phone", "mac", "server"):
                handler.join_physical_room({"join_token": room["join_token"], "label": label})
                node = handler.sent[1]
                node_tokens.append(node["node_token"])
                handler.ready_physical_node(
                    {
                        "node_token": node["node_token"],
                        "metrics": {
                            "accuracy": 1.0,
                            "delta_norm": 12.0 + node["role"],
                            "weight_checksum": f"weights-{node['role']}",
                            "runtime": "test",
                        },
                    }
                )
            handler.start_physical_room({"owner_token": owner_token, "task_count": 32})
            self.assertEqual(handler.sent[0], HTTPStatus.OK)
            for token in node_tokens:
                handler.physical_status({"token": token})
                status = handler.sent[1]
                table = status["training_table"]
                capsules = []
                for key in status["task_keys"]:
                    target = table[key]
                    capsules.append([8.0 if index == target else -1.0 for index in range(16)])
                handler.contribute_physical_node(
                    {"node_token": token, "capsules": capsules}
                )
            handler.physical_status({"token": owner_token})
            final = handler.sent[1]
            self.assertEqual(final["status"], "complete")
            self.assertEqual(final["result"]["exact_accuracy"], 1.0)
            self.assertEqual(final["result"]["answer_space"], 4096)
            self.assertTrue(
                all(value < 1 for value in final["result"]["remove_one_accuracy"])
            )
            handler.publish_physical_room({"owner_token": owner_token, "consent": True})
            self.assertEqual(handler.sent[0], HTTPStatus.OK)
            self.assertEqual(handler.public_physical_rooms()[0]["public_id"], room["room_id"])

    def test_physical_tasks_are_deterministic_and_private_shards_are_bounded(self):
        self.assertEqual(physical_tasks("N0001", 5), physical_tasks("N0001", 5))
        table = new_physical_table()
        self.assertEqual(len(table), 16)
        self.assertTrue(all(0 <= value < 16 for value in table))


if __name__ == "__main__":
    unittest.main()

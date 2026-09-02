from __future__ import annotations

import unittest

from pocket_i_core import (
    CandidateEvidence,
    Conversation,
    EvidenceSpan,
    HarnessModules,
    Message,
    PocketICore,
    ShelfPlan,
)


def conversation(identifier: str, text: str) -> Conversation:
    return Conversation(identifier, "fixture", (Message(f"{identifier}:1", "assistant", text),))


def candidate(identifier: str, conversation_id: str, quote: str, claim: str | None = None) -> CandidateEvidence:
    return CandidateEvidence(
        identifier,
        conversation_id,
        claim or quote,
        (EvidenceSpan(f"{conversation_id}:1", quote),),
        "fixture-v1",
    )


class PipelineTests(unittest.TestCase):
    def modules(self, *, candidates, shelves=None, secrets=(), approvals=None, writer_seen=None):
        candidates_by_chat = {}
        for item in candidates:
            candidates_by_chat.setdefault(item.conversation_id, []).append(item)
        approvals = approvals or {}

        def write(question, used):
            if writer_seen is not None:
                writer_seen.extend(item.candidate_id for item in used)
            return "Together: " + " ".join(item.claim for item in used)

        return HarnessModules(
            route=lambda question, chats, top_k: [chat.conversation_id for chat in chats[:top_k]],
            read=lambda question, chat: candidates_by_chat.get(chat.conversation_id, []),
            scan_secrets=lambda item: secrets if item.candidate_id == "secret" else (),
            approve=lambda item: approvals.get(item.candidate_id, True),
            nli=lambda question, item: "entailment",
            build_shelves=lambda question, checked: shelves
            or ShelfPlan(tuple(item.candidate.candidate_id for item in checked), ()),
            write=write,
        )

    def test_happy_path_keeps_alternatives_away_from_writer(self):
        chats = [conversation("c1", "Cause is phase drift."), conversation("c2", "A minority report says heat rebound.")]
        evidence = [
            candidate("main", "c1", "Cause is phase drift."),
            candidate("alternative", "c2", "A minority report says heat rebound."),
        ]
        writer_seen = []
        core = PocketICore(
            self.modules(
                candidates=evidence,
                shelves=ShelfPlan(("main",), ("alternative",)),
                writer_seen=writer_seen,
            )
        )

        result = core.run("What caused the fault?", chats)

        self.assertEqual("answered", result.status)
        self.assertEqual(["main"], writer_seen)
        self.assertEqual(("main",), tuple(item.candidate_id for item in result.used))
        self.assertEqual(("alternative",), tuple(item.candidate_id for item in result.alternatives))
        self.assertEqual(["question", "route", "read", "accept", "shelves", "write"], [event.step for event in result.trace])

    def test_non_exact_quote_is_rejected_before_owner_approval(self):
        chat = conversation("c1", "Power must be isolated first.")
        bad = candidate("bad", "c1", "Power can stay on.")
        core = PocketICore(self.modules(candidates=[bad]))

        result = core.run("What should I do?", [chat])

        self.assertEqual("no_information", result.status)
        self.assertEqual("source span is not exact", result.checked[0].rejection_reason)
        self.assertFalse(result.checked[0].owner_approved)

    def test_secret_and_owner_rejection_fail_closed(self):
        chats = [conversation("c1", "Token abc belongs here."), conversation("c2", "Safe public fact.")]
        evidence = [candidate("secret", "c1", "Token abc belongs here."), candidate("denied", "c2", "Safe public fact.")]
        core = PocketICore(self.modules(candidates=evidence, secrets=("credential",), approvals={"denied": False}))

        result = core.run("What can leave the device?", chats)

        self.assertEqual("no_information", result.status)
        self.assertEqual(["secret scanner blocked the capsule", "owner did not approve the capsule"], [item.rejection_reason for item in result.checked])

    def test_neutral_source_claim_is_recorded_and_blocked_before_shelves(self):
        chat = conversation("c1", "The exact source statement.")
        item = candidate("e1", "c1", "The exact source statement.")
        modules = self.modules(candidates=[item])
        modules = HarnessModules(
            modules.route,
            modules.read,
            modules.scan_secrets,
            modules.approve,
            lambda question, evidence: "neutral",
            modules.build_shelves,
            modules.write,
        )

        result = PocketICore(modules).run("Does this help?", [chat])

        self.assertEqual("no_information", result.status)
        self.assertEqual("neutral", result.checked[0].nli_signal)
        self.assertFalse(result.checked[0].accepted)
        self.assertEqual("source does not entail the proposed claim", result.checked[0].rejection_reason)

    def test_shelves_must_account_for_every_accepted_candidate(self):
        chat = conversation("c1", "One fact.")
        item = candidate("e1", "c1", "One fact.")
        core = PocketICore(self.modules(candidates=[item], shelves=ShelfPlan((), ())))

        with self.assertRaisesRegex(ValueError, "preserve every accepted"):
            core.run("Question", [chat])

    def test_empty_route_returns_fixed_answer_without_writer(self):
        calls = []
        modules = HarnessModules(
            route=lambda question, chats, top_k: (),
            read=lambda question, chat: (),
            scan_secrets=lambda item: (),
            approve=lambda item: True,
            nli=lambda question, item: "unavailable",
            build_shelves=lambda question, checked: ShelfPlan((), ()),
            write=lambda question, used: calls.append("writer") or "wrong",
        )

        result = PocketICore(modules).run("Unknown question", [])

        self.assertEqual("no_information", result.status)
        self.assertEqual(PocketICore.NO_INFORMATION, result.answer)
        self.assertEqual([], calls)


if __name__ == "__main__":
    unittest.main()

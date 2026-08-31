"""One fail-closed harness path shared by every desktop build.

The core owns order, validation and the audit trace. Models remain replaceable
modules behind small callables. This prevents a platform wrapper or model
preset from silently skipping evidence verification, secret screening or owner
approval.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Callable, Literal, Sequence


NliLabel = Literal["entailment", "neutral", "contradiction", "unavailable"]


@dataclass(frozen=True)
class Message:
    coordinate: str
    role: Literal["user", "assistant"]
    text: str


@dataclass(frozen=True)
class Conversation:
    conversation_id: str
    source: Literal["codex", "claude_code", "chatgpt_desktop", "fixture"]
    messages: tuple[Message, ...]


@dataclass(frozen=True)
class EvidenceSpan:
    coordinate: str
    quote: str


@dataclass(frozen=True)
class CandidateEvidence:
    candidate_id: str
    conversation_id: str
    claim: str
    spans: tuple[EvidenceSpan, ...]
    source_version: str


@dataclass(frozen=True)
class CheckedEvidence:
    candidate: CandidateEvidence
    exact_source: bool
    secret_findings: tuple[str, ...]
    owner_approved: bool
    nli_signal: NliLabel
    accepted: bool
    rejection_reason: str | None


@dataclass(frozen=True)
class ShelfPlan:
    used: tuple[str, ...]
    alternatives: tuple[str, ...]


@dataclass(frozen=True)
class TraceEvent:
    step: str
    state: Literal["ok", "empty", "blocked", "failed"]
    detail: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class PipelineResult:
    status: Literal["answered", "no_information"]
    answer: str
    used: tuple[CandidateEvidence, ...]
    alternatives: tuple[CandidateEvidence, ...]
    checked: tuple[CheckedEvidence, ...]
    trace: tuple[TraceEvent, ...]

    def audit_dict(self) -> dict[str, object]:
        """Return a JSON-ready local audit. Source texts stay in local objects."""
        return {
            "status": self.status,
            "answer": self.answer,
            "used_candidate_ids": [item.candidate_id for item in self.used],
            "alternative_candidate_ids": [item.candidate_id for item in self.alternatives],
            "checked": [
                {
                    "candidate_id": item.candidate.candidate_id,
                    "exact_source": item.exact_source,
                    "secret_findings": list(item.secret_findings),
                    "owner_approved": item.owner_approved,
                    "nli_signal": item.nli_signal,
                    "accepted": item.accepted,
                    "rejection_reason": item.rejection_reason,
                }
                for item in self.checked
            ],
            "trace": [asdict(event) for event in self.trace],
        }


Router = Callable[[str, Sequence[Conversation], int], Sequence[str]]
Reader = Callable[[str, Conversation], Sequence[CandidateEvidence]]
SecretScanner = Callable[[CandidateEvidence], Sequence[str]]
OwnerApproval = Callable[[CandidateEvidence], bool]
NliJudge = Callable[[str, CandidateEvidence], NliLabel]
ShelfBuilder = Callable[[str, Sequence[CheckedEvidence]], ShelfPlan]
Writer = Callable[[str, Sequence[CandidateEvidence]], str]


@dataclass(frozen=True)
class HarnessModules:
    route: Router
    read: Reader
    scan_secrets: SecretScanner
    approve: OwnerApproval
    nli: NliJudge
    build_shelves: ShelfBuilder
    write: Writer


class PocketICore:
    """Run one question through the accepted MVP order."""

    NO_INFORMATION = "The network did not return supported information."

    def __init__(self, modules: HarnessModules, *, top_k: int = 5) -> None:
        if top_k < 1:
            raise ValueError("top_k must be positive")
        self.modules = modules
        self.top_k = top_k

    def run(self, question: str, conversations: Sequence[Conversation]) -> PipelineResult:
        question = question.strip()
        if not question:
            raise ValueError("question must not be empty")

        trace: list[TraceEvent] = [TraceEvent("question", "ok", {"characters": len(question)})]
        by_id = self._conversation_index(conversations)
        routed_ids = tuple(dict.fromkeys(self.modules.route(question, conversations, self.top_k)))
        if len(routed_ids) > self.top_k:
            raise ValueError("router returned more conversations than top_k")
        unknown_routes = [item for item in routed_ids if item not in by_id]
        if unknown_routes:
            raise ValueError(f"router returned unknown conversations: {unknown_routes}")
        trace.append(TraceEvent("route", "ok" if routed_ids else "empty", {"conversation_ids": list(routed_ids)}))

        candidates: list[CandidateEvidence] = []
        candidate_ids: set[str] = set()
        for conversation_id in routed_ids:
            for candidate in self.modules.read(question, by_id[conversation_id]):
                if candidate.conversation_id != conversation_id:
                    raise ValueError("reader returned evidence for a different conversation")
                if not candidate.candidate_id or candidate.candidate_id in candidate_ids:
                    raise ValueError("candidate IDs must be non-empty and unique")
                candidate_ids.add(candidate.candidate_id)
                candidates.append(candidate)
        trace.append(TraceEvent("read", "ok" if candidates else "empty", {"candidate_ids": [item.candidate_id for item in candidates]}))

        checked = tuple(self._check(question, candidate, by_id[candidate.conversation_id]) for candidate in candidates)
        accepted = tuple(item for item in checked if item.accepted)
        trace.append(
            TraceEvent(
                "accept",
                "ok" if accepted else "empty",
                {
                    "accepted_ids": [item.candidate.candidate_id for item in accepted],
                    "rejected_ids": [item.candidate.candidate_id for item in checked if not item.accepted],
                },
            )
        )

        if not accepted:
            trace.append(TraceEvent("write", "empty", {"reason": "no accepted evidence"}))
            return PipelineResult("no_information", self.NO_INFORMATION, (), (), checked, tuple(trace))

        shelves = self.modules.build_shelves(question, accepted)
        used, alternatives = self._validate_shelves(shelves, accepted)
        trace.append(TraceEvent("shelves", "ok", {"used": list(shelves.used), "alternatives": list(shelves.alternatives)}))

        if not used:
            trace.append(TraceEvent("write", "empty", {"reason": "used shelf is empty"}))
            return PipelineResult("no_information", self.NO_INFORMATION, (), alternatives, checked, tuple(trace))

        answer = self.modules.write(question, used).strip()
        if not answer:
            raise ValueError("writer returned an empty answer")
        trace.append(TraceEvent("write", "ok", {"used_candidate_ids": [item.candidate_id for item in used]}))
        return PipelineResult("answered", answer, used, alternatives, checked, tuple(trace))

    @staticmethod
    def _conversation_index(conversations: Sequence[Conversation]) -> dict[str, Conversation]:
        result: dict[str, Conversation] = {}
        for conversation in conversations:
            if not conversation.conversation_id or conversation.conversation_id in result:
                raise ValueError("conversation IDs must be non-empty and unique")
            coordinates = [message.coordinate for message in conversation.messages]
            if len(coordinates) != len(set(coordinates)):
                raise ValueError("message coordinates must be unique inside a conversation")
            result[conversation.conversation_id] = conversation
        return result

    def _check(self, question: str, candidate: CandidateEvidence, conversation: Conversation) -> CheckedEvidence:
        messages = {message.coordinate: message.text for message in conversation.messages}
        exact = bool(candidate.spans) and all(
            span.coordinate in messages and bool(span.quote) and span.quote in messages[span.coordinate]
            for span in candidate.spans
        )
        if not exact:
            return CheckedEvidence(candidate, False, (), False, "unavailable", False, "source span is not exact")

        findings = tuple(self.modules.scan_secrets(candidate))
        if findings:
            return CheckedEvidence(candidate, True, findings, False, "unavailable", False, "secret scanner blocked the capsule")

        approved = bool(self.modules.approve(candidate))
        if not approved:
            return CheckedEvidence(candidate, True, (), False, "unavailable", False, "owner did not approve the capsule")

        signal = self.modules.nli(question, candidate)
        if signal not in {"entailment", "neutral", "contradiction", "unavailable"}:
            raise ValueError(f"unknown NLI signal: {signal}")
        # E007 showed that DeBERTa has weak recall. Preserve its signal, but do
        # not let it silently delete exact, owner-approved evidence.
        return CheckedEvidence(candidate, True, (), True, signal, True, None)

    @staticmethod
    def _validate_shelves(
        shelves: ShelfPlan, accepted: Sequence[CheckedEvidence]
    ) -> tuple[tuple[CandidateEvidence, ...], tuple[CandidateEvidence, ...]]:
        accepted_by_id = {item.candidate.candidate_id: item.candidate for item in accepted}
        assigned = tuple(shelves.used) + tuple(shelves.alternatives)
        if len(assigned) != len(set(assigned)):
            raise ValueError("a candidate may appear on only one shelf")
        if set(assigned) != set(accepted_by_id):
            raise ValueError("shelves must preserve every accepted candidate exactly once")
        return (
            tuple(accepted_by_id[item] for item in shelves.used),
            tuple(accepted_by_id[item] for item in shelves.alternatives),
        )


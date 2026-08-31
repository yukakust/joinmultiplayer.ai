"""Portable orchestration core for the Pocket i desktop MVP."""

from .pipeline import (
    CandidateEvidence,
    Conversation,
    EvidenceSpan,
    HarnessModules,
    Message,
    PipelineResult,
    PocketICore,
    ShelfPlan,
)
from .library import AdapterStatus, LocalLibrary, scan_local_library

__all__ = [
    "CandidateEvidence",
    "Conversation",
    "EvidenceSpan",
    "HarnessModules",
    "Message",
    "PipelineResult",
    "PocketICore",
    "ShelfPlan",
    "AdapterStatus",
    "LocalLibrary",
    "scan_local_library",
]


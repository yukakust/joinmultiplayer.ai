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
from .library import (
    AdapterStatus,
    ConversationCount,
    LocalLibrary,
    LocalLibraryCounts,
    count_local_conversations,
    scan_local_library,
)
from .retrieval import HybridChatIndex, RouteResult
from .index_cache import CacheStats, build_cached_index

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
    "ConversationCount",
    "LocalLibrary",
    "LocalLibraryCounts",
    "count_local_conversations",
    "scan_local_library",
    "HybridChatIndex",
    "RouteResult",
    "CacheStats",
    "build_cached_index",
]

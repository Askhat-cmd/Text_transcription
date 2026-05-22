"""Configuration constants for Memory + Retrieval agent."""

from ...feature_flags import feature_flags

CONVERSATION_TURNS_BY_PHASE: dict[str, int] = {
    "stabilize": 3,
    "clarify": 6,
    "explore": 6,
    "integrate": 10,
}
CONVERSATION_TURNS_DEFAULT: int = int(
    feature_flags.value("MEMORY_CONV_TURNS_DEFAULT", "6") or "6"
)
CONVERSATION_TURNS_NEW_THREAD: int = 5

RAG_N_RESULTS: int = int(feature_flags.value("MEMORY_RAG_N_RESULTS", "4") or "4")
RAG_MIN_SCORE: float = float(feature_flags.value("MEMORY_RAG_MIN_SCORE", "0.45") or "0.45")
RAG_QUERY_MAX_LEN: int = 300
RAG_SCORE_POLICY_V1_ENABLED: bool = str(
    feature_flags.value("MEMORY_RAG_SCORE_POLICY_V1_ENABLED", "true") or "true"
).strip().lower() in {"1", "true", "yes", "on"}
RAG_LOW_SCORE_SALVAGE_ENABLED: bool = str(
    feature_flags.value("MEMORY_RAG_LOW_SCORE_SALVAGE_ENABLED", "true") or "true"
).strip().lower() in {"1", "true", "yes", "on"}
RAG_LOW_SCORE_SALVAGE_MAX_HITS: int = int(
    feature_flags.value("MEMORY_RAG_LOW_SCORE_SALVAGE_MAX_HITS", "3") or "3"
)
RAG_LOW_SCORE_SALVAGE_MIN_TOP_SCORE: float = float(
    feature_flags.value("MEMORY_RAG_LOW_SCORE_SALVAGE_MIN_TOP_SCORE", "0.03") or "0.03"
)

CORE_DIRECTION_MIN_LEN: int = 10

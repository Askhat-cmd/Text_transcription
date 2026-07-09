# api/admin_routes.py
"""
Admin Config Panel вЂ” API endpoints.

Все эндпоинты требуют dev-ключ в заголовке X-API-Key.
Роутер регистрируется в main.py через app.include_router(admin_router).
"""

from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from typing import Any
import importlib
import json
import logging
import os
import threading as _threading
from collections import deque as _deque
from datetime import datetime, timezone
from pathlib import Path

from bot_agent.config import config
from bot_agent.config_validation import validate_runtime_config
from bot_agent.data_loader import data_loader
from bot_agent.feature_flags import feature_flags
from bot_agent.multiagent.orchestrator import orchestrator
from bot_agent.multiagent.dialogue_policy import (
    ALLOWED_DIALOGUE_PROFILES,
    DIALOGUE_PROFILE_CUSTOM_DEV,
    DIALOGUE_PROFILE_MVP_FREE,
    UNIFIED_DIALOGUE_POLICY_VERSION,
    build_effective_dialogue_policy,
    normalize_dialogue_profile,
    resolve_profile_preset,
)
from bot_agent.multiagent.final_answer_directive import FINAL_ANSWER_DIRECTIVE_VERSION
from bot_agent.multiagent.final_answer_acceptance_gate import FINAL_ANSWER_ACCEPTANCE_GATE_VERSION
from bot_agent.multiagent.fresh_chat_context_policy import FRESH_CHAT_CONTEXT_POLICY_VERSION
from bot_agent.multiagent.hybrid_retrieval_planner import (
    HYBRID_RETRIEVAL_PLANNER_VERSION,
    get_hybrid_retrieval_planner_settings,
)
from bot_agent.multiagent.planner_drift_monitor import get_planner_drift_summary
from bot_agent.multiagent.philosophy_kernel import (
    KERNEL_V1,
    WRITER_FREEDOM_CONTRACT_VERSION,
)
from bot_agent.multiagent.thread_storage import thread_storage
from bot_agent.multiagent.writer_context_package import WRITER_CONTEXT_PACKAGE_VERSION
from bot_agent.knowledge.semantic_card_payload_adapter import build_semantic_cards_runtime_status
from bot_agent.diagnostic_center_control import (
    apply_diagnostic_center_control_update,
    build_diagnostic_center_effective_payload,
    reset_diagnostic_center_control_state,
)
from bot_agent.effective_config_registry import (
    build_compat_env_flags_snapshot,
    build_effective_config_payload,
)
from bot_agent.multiagent.agents.agent_llm_config import (
    ALLOWED_MODELS,
    get_all_agent_models,
    set_temperature_for_agent,
    reset_temperature_for_agent,
    set_model_for_agent,
    reset_model_for_agent,
)
from bot_agent.prompt_registry_v2 import PROMPT_STACK_ORDER, PROMPT_STACK_VERSION, prompt_registry_v2
from .auth import is_dev_key
from .dependencies import get_identity_service
from .identity import IdentityService, mask_external_id

logger = logging.getLogger(__name__)

_agent_metrics_lock = _threading.Lock()
_agent_metrics: dict[str, dict[str, Any]] = {
    "state_analyzer": {"call_count": 0, "total_ms": 0, "error_count": 0, "last_run": None, "enabled": True},
    "thread_manager": {"call_count": 0, "total_ms": 0, "error_count": 0, "last_run": None, "enabled": True},
    "memory_retrieval": {"call_count": 0, "total_ms": 0, "error_count": 0, "last_run": None, "enabled": True},
    "writer": {"call_count": 0, "total_ms": 0, "error_count": 0, "last_run": None, "enabled": True},
    "validator": {"call_count": 0, "total_ms": 0, "error_count": 0, "last_run": None, "enabled": True},
}
_agent_traces: _deque[dict[str, Any]] = _deque(maxlen=200)
_orchestrator_mode: dict[str, str] = {"pipeline_mode": "multiagent_only"}
_agent_prompt_overrides: dict[str, dict[str, str]] = {}
_AGENT_PROMPT_MAP = {
    "writer": "bot_agent.multiagent.agents.writer_agent_prompts",
    "state_analyzer": "bot_agent.multiagent.agents.state_analyzer_prompts",
    "thread_manager": "bot_agent.multiagent.agents.thread_manager_prompts",
}

# ─── Auth dependency ───────────────────────────────────────────────────────────

def require_dev_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    """FastAPI Dependency: доступ только для dev-ключа."""
    if not is_dev_key(x_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Доступ запрещён: требуется dev-ключ",
        )
    return x_api_key


# ─── Router ────────────────────────────────────────────────────────────────────

admin_router = APIRouter(
    prefix="/api/admin",
    tags=["⚙️ Admin Config"],
    dependencies=[Depends(require_dev_key)],
)

admin_router_v1 = APIRouter(
    prefix="/api/v1/admin",
    tags=["⚙️ Admin Config v1"],
    dependencies=[Depends(require_dev_key)],
)

ADMIN_SCHEMA_VERSION = "10.5"
ADMIN_EFFECTIVE_SCHEMA_VERSION = "10.5.1"

LEGACY_CONFIG_KEY_MAP = {
    "RETRIEVAL_TOP_K": "TOP_K_BLOCKS",
    "RERANK_TOP_K": "VOYAGE_TOP_K",
}

DEPRECATED_CONFIG_KEYS: set[str] = {
    "FAST_DETECTOR_ENABLED",
    "STATE_CLASSIFIER_ENABLED",
    "DECISION_GATE_RULE_THRESHOLD",
    "DECISION_GATE_LLM_ROUTER_ENABLED",
    "PROMPT_MODE_OVERRIDES_SD",
}

COMPATIBILITY_ONLY_CONFIG_KEYS: set[str] = set()

DEPRECATED_PROMPT_KEYS: set[str] = set()

PROMPT_STACK_V2_VARIANTS = [
    "inform-rich",
    "mixed-query",
    "first-turn",
    "user-correction",
    "safe-override",
]

PROMPT_STACK_V2_EDITABLE_MAP = {
    "CORE_IDENTITY": "prompt_system_base",
}

__all__ = [name for name in globals() if not name.startswith("__")]

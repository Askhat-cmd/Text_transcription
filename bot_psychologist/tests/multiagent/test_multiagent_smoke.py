from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.feature_flags import feature_flags
from bot_agent.multiagent.agents import (
    memory_retrieval_agent,
    state_analyzer_agent,
    thread_manager_agent,
    validator_agent,
    writer_agent,
)
from bot_agent.multiagent.contracts import (
    MemoryBundle,
    StateSnapshot,
    ThreadState,
    ValidationResult,
    WriterContract,
)
from bot_agent.multiagent.orchestrator import orchestrator
from bot_agent.multiagent.thread_storage import thread_storage


def _load_local_env() -> None:
    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(project_root / ".env", override=False)
    load_dotenv(project_root / ".env.example", override=False)


def test_sm_01_env_multiagent_key_exists() -> None:
    _load_local_env()
    assert "MULTIAGENT_ENABLED" in os.environ


def test_sm_02_state_analyzer_model_readable() -> None:
    _load_local_env()
    model = os.getenv("STATE_ANALYZER_MODEL")
    assert isinstance(model, str)
    assert model.strip() != ""


def test_sm_03_writer_model_readable() -> None:
    _load_local_env()
    model = os.getenv("WRITER_MODEL")
    assert isinstance(model, str)
    assert model.strip() != ""


def test_sm_04_orchestrator_importable() -> None:
    assert orchestrator is not None
    assert hasattr(orchestrator, "run")


def test_sm_05_all_agents_importable() -> None:
    assert state_analyzer_agent is not None
    assert thread_manager_agent is not None
    assert memory_retrieval_agent is not None
    assert writer_agent is not None
    assert validator_agent is not None


def test_sm_06_all_contracts_importable() -> None:
    assert StateSnapshot is not None
    assert ThreadState is not None
    assert MemoryBundle is not None
    assert WriterContract is not None
    assert ValidationResult is not None


def test_sm_07_feature_flag_readable() -> None:
    _load_local_env()
    value = feature_flags.is_enabled("MULTIAGENT_ENABLED")
    assert isinstance(value, bool)


def test_sm_08_thread_storage_init() -> None:
    result = thread_storage.load_active("smoke_test_user")
    assert result is None or isinstance(result, ThreadState)


def test_sm_09_timeout_value_valid() -> None:
    _load_local_env()
    timeout_raw = os.getenv("MULTIAGENT_LLM_TIMEOUT")
    if timeout_raw is None:
        return
    assert float(timeout_raw) > 0


def test_sm_10_max_tokens_value_valid() -> None:
    _load_local_env()
    max_tokens_raw = os.getenv("MULTIAGENT_MAX_TOKENS")
    if max_tokens_raw is None:
        return
    assert int(max_tokens_raw) > 0


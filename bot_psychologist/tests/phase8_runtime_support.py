from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Callable, Dict, Optional

from bot_agent.data_loader import Block
from bot_agent.diagnostics_classifier import DiagnosticsConfidence, DiagnosticsV1
from bot_agent.state_classifier import StateAnalysis, UserState


@dataclass(frozen=True)
class SDClassificationResult:
    primary: str
    secondary: Optional[str] = None
    confidence: float = 0.0
    indicator: str = "disabled_by_design"
    method: str = "disabled"
    allowed_blocks: list[str] = field(default_factory=list)


class DummyMemory:
    def __init__(self, *, turns_count: int = 0) -> None:
        self.summary = ""
        self.summary_updated_at = None
        self.semantic_memory = SimpleNamespace(last_hits_detail=[], last_hits_count=0)
        self.metadata: Dict[str, object] = {}
        self.working_state = None
        self.turns = [SimpleNamespace(user_input="u", bot_response="b") for _ in range(turns_count)]

    def get_adaptive_context_text(self, _query: str) -> str:
        return ""

    def get_last_turns(self, _n: int):
        return []

    def get_turns_preview(self):
        return []

    def get_user_sd_profile(self):
        return {}

    def update_sd_profile(self, *_args, **_kwargs):
        return None

    def set_working_state(self, working_state):
        self.working_state = working_state

    def add_turn(self, user_input: str, bot_response: str, **_kwargs):
        self.turns.append(
            SimpleNamespace(
                user_input=user_input,
                bot_response=bot_response,
                user_state=None,
                blocks_used=0,
                concepts=[],
            )
        )

    def get_summary(self) -> str:
        return self.summary

    def load_cross_session_context(self, *_args, **_kwargs) -> str:
        return ""

    def get_primary_interests(self):
        return []


class DummyRetriever:
    def retrieve(self, _query, top_k=None, author_id=None):
        size = int(top_k or 5)
        return [
            (
                Block(
                    block_id=f"b{idx}",
                    title=f"T{idx}",
                    content=f"C{idx}",
                    document_title="Doc",
                ),
                0.9 - idx * 0.01,
            )
            for idx in range(size)
        ]


class DummyAnswerer:
    @staticmethod
    def build_system_prompt() -> str:
        return "SYSTEM"

    @staticmethod
    def build_context_prompt(*_args, **_kwargs) -> str:
        return "USER"


class DummyResponseGenerator:
    def __init__(self, answer_text: str, capture: Dict[str, object]) -> None:
        self._answer_text = answer_text
        self.answerer = DummyAnswerer()
        self._capture = capture

    def generate(self, query, blocks, **kwargs):
        self._capture["query"] = query
        self._capture["blocks"] = blocks
        self._capture["kwargs"] = kwargs
        return {
            "answer": self._answer_text,
            "model_used": "dummy-model",
            "tokens_prompt": 11,
            "tokens_completion": 13,
            "tokens_total": 24,
            "llm_call_info": {},
        }


@dataclass(frozen=True)
class RuntimeHarness:
    memory: DummyMemory
    llm_capture: Dict[str, object]


def build_state_analysis() -> StateAnalysis:
    return StateAnalysis(
        primary_state=UserState.CURIOUS,
        confidence=0.74,
        secondary_states=[],
        indicators=[],
        emotional_tone="neutral",
        depth="intermediate",
        recommendations=["stay focused"],
    )


def build_sd_result() -> SDClassificationResult:
    return SDClassificationResult(
        primary="GREEN",
        secondary=None,
        confidence=0.8,
        indicator="test",
        method="mock",
    )


def build_diagnostics(
    *,
    interaction_mode: str = "coaching",
    nervous_system_state: str = "window",
    request_function: str = "understand",
    core_theme: str = "core_theme",
    interaction_conf: float = 0.9,
    nervous_conf: float = 0.8,
    request_conf: float = 0.9,
) -> DiagnosticsV1:
    return DiagnosticsV1(
        interaction_mode=interaction_mode,
        nervous_system_state=nervous_system_state,
        request_function=request_function,
        core_theme=core_theme,
        confidence=DiagnosticsConfidence(
            interaction_mode=interaction_conf,
            nervous_system_state=nervous_conf,
            request_function=request_conf,
            core_theme=0.7,
        ),
        optional={},
    )


def setup_phase8_runtime(
    monkeypatch,
    aa_module,
    *,
    turns_count: int = 0,
    informational_branch_enabled: bool = True,
    diagnostics_builder: Optional[Callable[..., DiagnosticsV1]] = None,
    answer_text: str = "Ответ по делу.",
) -> RuntimeHarness:
    memory = DummyMemory(turns_count=turns_count)
    llm_capture: Dict[str, object] = {}

    def _flags(name: str) -> bool:
        mapping = {
            "INFORMATIONAL_BRANCH_ENABLED": informational_branch_enabled,
            "USE_NEW_DIAGNOSTICS_V1": True,
            "USE_DETERMINISTIC_ROUTE_RESOLVER": True,
            "USE_PROMPT_STACK_V2": True,
            "USE_OUTPUT_VALIDATION": False,
            "ENABLE_CONDITIONAL_RERANKER": False,
            "ENABLE_FAST_STATE_DETECTOR": False,
            "ENABLE_FAST_SD_DETECTOR": False,
            "DISABLE_SD_RUNTIME": False,
        }
        return bool(mapping.get(name, False))

    monkeypatch.setattr(aa_module.feature_flags, "enabled", _flags)
    monkeypatch.setattr(aa_module.data_loader, "load_all_data", lambda: None)
    monkeypatch.setattr(aa_module, "get_conversation_memory", lambda _user_id: memory)
    monkeypatch.setattr(aa_module, "_should_use_fast_path", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(aa_module, "get_retriever", lambda: DummyRetriever())
    monkeypatch.setattr(aa_module.config, "AUTHOR_BLEND_MODE", "off")
    monkeypatch.setattr(
        aa_module.config,
        "_load_overrides",
        lambda: {"config": {}, "prompts": {}, "meta": {}, "history": []},
    )

    async def _fake_classify_parallel(*_args, **_kwargs):
        return build_state_analysis(), build_sd_result()

    monkeypatch.setattr(aa_module, "_classify_parallel", _fake_classify_parallel)

    if diagnostics_builder is None:
        diagnostics_builder = (
            lambda query, state_analysis, informational_mode_hint=False: build_diagnostics(
                interaction_mode="coaching"
            )
        )

    monkeypatch.setattr(
        aa_module.diagnostics_classifier,
        "classify",
        lambda query, state_analysis, informational_mode_hint=False: diagnostics_builder(
            query=query,
            state_analysis=state_analysis,
            informational_mode_hint=informational_mode_hint,
        ),
    )

    monkeypatch.setattr(
        aa_module.memory_updater,
        "build_runtime_context",
        lambda **_kwargs: SimpleNamespace(
            context=SimpleNamespace(
                context_text="",
                summary_used=False,
                staleness="fresh",
                strategy="fresh_summary_small_window",
            ),
            snapshot={"schema_version": "1.1"},
        ),
    )
    monkeypatch.setattr(aa_module.memory_updater, "save_snapshot", lambda *_args, **_kwargs: None)

    monkeypatch.setattr(
        aa_module,
        "ResponseGenerator",
        lambda: DummyResponseGenerator(answer_text=answer_text, capture=llm_capture),
    )

    return RuntimeHarness(memory=memory, llm_capture=llm_capture)

"""Prompt Stack v2 builder for Neo MindBot."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Dict, Iterable, List, Optional

from .config import config


PROMPT_STACK_VERSION = "2.0"
PROMPT_STACK_ORDER = (
    "AA_SAFETY",
    "A_SEASONAL",
    "CORE_IDENTITY",
    "DIAG_ALGORITHM",
    "REFLECTIVE_METHOD",
    "PROCEDURAL_SCRIPTS",
    "OUTPUT_LAYER",
)
PROMPTS_DIR = Path(__file__).resolve().with_name("prompts")


@dataclass(frozen=True)
class PromptStackBuild:
    version: str
    order: List[str]
    sections: Dict[str, str]
    system_prompt: str

    def as_dict(self) -> Dict[str, object]:
        return {
            "version": self.version,
            "order": list(self.order),
            "sections": {k: len(self.sections.get(k, "")) for k in self.order},
        }


class PromptRegistryV2:
    """Builds deterministic prompt stack with a fixed section order."""

    version = PROMPT_STACK_VERSION
    order = PROMPT_STACK_ORDER

    @staticmethod
    def _clip(text: str, limit: int) -> str:
        raw = (text or "").strip()
        if len(raw) <= limit:
            return raw
        return raw[: max(0, limit - 3)].rstrip() + "..."

    @staticmethod
    def _join_parts(parts: Iterable[str]) -> str:
        return "\n\n".join(part for part in parts if part and part.strip()).strip()

    def _load_prompt_asset(self, filename: str, fallback: str) -> str:
        path = PROMPTS_DIR / filename
        try:
            if path.exists():
                return path.read_text(encoding="utf-8").strip()
        except Exception:
            pass
        return fallback.strip()

    @staticmethod
    def _render_template(template: str, **values: str) -> str:
        try:
            return (template or "").format(**values)
        except Exception:
            return template or ""

    def _load_core_identity(self) -> str:
        try:
            return str(config.get_prompt("prompt_system_base")["text"]).strip()
        except Exception:
            return (
                "You are a reflective assistant. "
                "Your role is to help the user clarify internal process without pressure."
            )

    def _build_style_policy(self, route: str, mode: str) -> str:
        normalized_route = (route or "").strip().lower()
        normalized_mode = (mode or "").strip().upper()
        if normalized_route == "safe_override":
            return (
                "Стиль: коротко, спокойно, деэскалирующе. "
                "Без рискованных директив и без глубокой интерпретации."
            )
        if normalized_route == "inform" or normalized_mode == "CLARIFICATION":
            return (
                "Объясняй живо и по существу: раскрывай смысл, а не только термин. "
                "Добавляй 2-4 коротких примера и показывай практический смысл. "
                "Избегай сухого FAQ и канцелярита. "
                "Не сокращай ответ искусственно."
            )
        if normalized_route == "regulate":
            return (
                "Стиль: сначала признание состояния — покажи, что слышишь и понимаешь. "
                "Затем раскрой контекст: что стоит за этим переживанием. "
                "Потом один конкретный посильный шаг. "
                "Минимум 3 содержательных предложения. "
                "Не сводить ответ к одному отражению + вопросу."
            )
        if normalized_route in ("contact_hold", "contact"):
            return (
                "Стиль: живой отклик на переживание пользователя, "
                "затем его контекст и смысл, затем практический ориентир. "
                "Минимум 3 содержательных предложения. "
                "Не сводить ответ к одному отражению + вопросу."
            )
        if normalized_route == "stabilize":
            return (
                "Стиль: спокойствие и опора. Сначала стабилизация присутствием, "
                "затем ориентир — что сейчас можно сделать. "
                "Минимум 3 содержательных предложения."
            )
        return (
            "Стиль: диалог с опорой на коучинговую точность, "
            "уважительно и без пустых обобщений. "
            "Минимум 3 содержательных предложения по существу."
        )

    def _build_memory_context(self, conversation_context: str) -> str:
        context = self._clip(self._sanitize_memory_context(conversation_context or ""), 1200)
        if not context:
            return "Conversation context: none."
        return f"Conversation context:\n{context}"

    @staticmethod
    def _sanitize_memory_context(context: str) -> str:
        """Fix mojibake (UTF-8 bytes read as latin-1) and drop snapshot block."""
        # --- encoding guard: fix UTF-8 bytes misread as latin-1 ---
        if isinstance(context, bytes):
            context = context.decode("utf-8", errors="replace")
        else:
            try:
                context = context.encode("latin-1").decode("utf-8")
            except (UnicodeDecodeError, UnicodeEncodeError):
                pass  # already valid unicode, no action needed
        # --- drop snapshot block to avoid duplicate diagnostics ---
        lines = []
        skipping_snapshot_block = False
        for line in (context or "").splitlines():
            normalized = line.strip().lower()
            if normalized == "snapshot:":
                skipping_snapshot_block = True
                continue
            if skipping_snapshot_block:
                if not normalized:
                    skipping_snapshot_block = False
                continue
            lines.append(line)
        return "\n".join(lines).strip()

    @staticmethod
    def _validate_prompt_consistency(system_prompt: str) -> None:
        values = re.findall(r"nervous_system_state[:\s]+([a-z_]+)", (system_prompt or "").lower())
        unique_values = sorted(set(values))
        if len(unique_values) > 1:
            raise ValueError(
                "PROMPT CONFLICT: nervous_system_state has multiple values: "
                + ", ".join(unique_values)
            )

    def _build_diagnostic_context(
        self,
        diagnostics: Optional[Dict[str, object]],
        route: str,
        mode: str,
    ) -> str:
        payload = diagnostics or {}
        interaction_mode = str(payload.get("interaction_mode") or "coaching")
        nervous_state = str(payload.get("nervous_system_state") or "window")
        request_function = str(payload.get("request_function") or "understand")
        core_theme = str(payload.get("core_theme") or "unspecified_current_issue")
        return (
            "Diagnostics context:\n"
            f"- interaction_mode: {interaction_mode}\n"
            f"- nervous_system_state: {nervous_state}\n"
            f"- request_function: {request_function}\n"
            f"- core_theme: {self._clip(core_theme, 180)}\n"
            f"- resolved_route: {route or 'reflect'}\n"
            f"- llm_mode: {mode or 'PRESENCE'}"
        )

    def _build_retrieved_context(self, blocks: List[object]) -> str:
        if not blocks:
            return "Knowledge context: no retrieved blocks."
        lines: List[str] = []
        for idx, block in enumerate(blocks[:6], start=1):
            title = str(getattr(block, "title", "") or getattr(block, "document_title", "")).strip()
            content = str(getattr(block, "summary", "") or getattr(block, "content", "")).strip()
            lines.append(f"[{idx}] {self._clip(title or 'Untitled', 90)}: {self._clip(content, 260)}")
        return "Knowledge context:\n" + "\n".join(lines)

    def _build_task_instruction(
        self,
        *,
        route: str,
        mode: str,
        query: str,
        mode_prompt_override: Optional[str],
        first_turn: bool = False,
        mixed_query_bridge: bool = False,
        user_correction_protocol: bool = False,
    ) -> str:
        route_text = (route or "reflect").strip().lower() or "reflect"
        mode_text = mode or "PRESENCE"
        parts = [
            "TASK_INSTRUCTION:",
            f"- Route: {route_text}",
            f"- Mode: {mode_text}",
            f"- User request: {self._clip(query, 700)}",
            "- Дай содержательный ответ без HTML/кода.",
            "- Для обычного запроса дай минимум 3 содержательных предложения.",
            "- Избегай смысловой скупости.",
            "- Не своди ответ к формату «одна мысль + один вопрос».",
        ]
        if mode_prompt_override:
            parts.append(f"- Mode override: {self._clip(mode_prompt_override, 260)}")
        if route_text == "inform":
            parts.extend(
                [
                    "- Раскрывай понятие в глубину и показывай практический смысл.",
                    "- Если запрос просит различия, сравни по 2-3 критериям.",
                    "- Не подменяй объяснение общим вопросом-мостом.",
                ]
            )
        if first_turn:
            parts.extend(
                [
                    "- Это первый ход: дай полноценный смысловой каркас как основу ответа.",
                    "- Warmup: не экономь на объёме — у модели пока нет контекста сессии.",
                    "- Допустим один уточняющий вопрос в конце, если он реально помогает.",
                    "- Не перегружай деталями, но оставь опорную ясность.",
                ]
            )
        if mixed_query_bridge:
            parts.extend(
                [
                    "- Сначала коротко обозначь концепт, затем свяжи его с запросом пользователя.",
                    "- Добавь практический угол и мягкий вопрос-мост.",
                ]
            )
        if user_correction_protocol:
            parts.extend(
                [
                    "- Протокол коррекции: признай несоответствие и откалибруй ответ.",
                    "- Корректирующий ответ должен содержать не менее 3 предложений.",
                    "- Заверши корректирующий ответ одним уточняющим вопросом.",
                ]
            )
        return "\n".join(parts)

    def _resolve_interaction_mode(self, diagnostics: Optional[Dict[str, object]]) -> str:
        payload = diagnostics or {}
        mode = str(payload.get("interaction_mode") or "").strip().lower()
        return mode if mode in {"informational", "coaching", "crisis"} else "coaching"

    def build(
        self,
        *,
        query: str,
        blocks: List[object],
        conversation_context: str,
        additional_system_context: str,
        route: str,
        mode: str,
        diagnostics: Optional[Dict[str, object]] = None,
        mode_prompt_override: Optional[str] = None,
        first_turn: bool = False,
        mixed_query_bridge: bool = False,
        user_correction_protocol: bool = False,
    ) -> PromptStackBuild:
        interaction_mode = self._resolve_interaction_mode(diagnostics)
        season = "neutral"

        aa_safety = self._load_prompt_asset(
            "aa_safety.md",
            "Safety Rules: no diagnosis, no treatment claims, no guarantees."
        )
        seasonal = self._load_prompt_asset(
            "a_seasonal.md",
            "Seasonal policy: season={season}, interaction_mode={interaction_mode}."
        )
        core_identity_static = self._load_prompt_asset("core_identity.md", "")
        diag_algorithm = self._load_prompt_asset("diag_algorithm.md", "Diagnostic algorithm: classify state and function.")
        reflective_method = self._load_prompt_asset("reflective_method.md", "Reflective Method: mirror, structure, clarify, next-step.")
        procedural_scripts = self._load_prompt_asset("procedural_scripts.md", "Procedural scripts: clear sequencing and correction protocol.")
        output_layer = self._load_prompt_asset(
            "output_layer.md",
            "Output layer: web-safe rich text. Minimum 3 substantive sentences. Avoid messenger-style brevity."
        )

        diagnostics_context = self._build_diagnostic_context(
            diagnostics=diagnostics,
            route=route,
            mode=mode,
        )
        memory_context = self._build_memory_context(conversation_context)
        retrieved_context = self._build_retrieved_context(blocks)
        task_instruction = self._build_task_instruction(
            route=route,
            mode=mode,
            query=query,
            mode_prompt_override=mode_prompt_override,
            first_turn=first_turn,
            mixed_query_bridge=mixed_query_bridge,
            user_correction_protocol=user_correction_protocol,
        )
        style_policy = self._build_style_policy(route=route, mode=mode)

        sections: Dict[str, str] = {
            "AA_SAFETY": aa_safety,
            "A_SEASONAL": self._join_parts(
                [
                    self._render_template(
                        seasonal,
                        season=season,
                        interaction_mode=interaction_mode,
                    ),
                    style_policy,
                ]
            ),
            "CORE_IDENTITY": self._join_parts([core_identity_static, self._load_core_identity()]),
            "DIAG_ALGORITHM": self._join_parts([diag_algorithm, diagnostics_context]),
            "REFLECTIVE_METHOD": self._join_parts([reflective_method, memory_context]),
            "PROCEDURAL_SCRIPTS": self._join_parts([procedural_scripts, retrieved_context]),
            "OUTPUT_LAYER": self._join_parts([output_layer, task_instruction]),
            "A_STYLE_POLICY": style_policy,
            "TASK_INSTRUCTION": task_instruction,
        }

        if additional_system_context and additional_system_context.strip():
            sections["DIAG_ALGORITHM"] = self._join_parts(
                [
                    sections["DIAG_ALGORITHM"],
                    f"Runtime context:\n{self._clip(additional_system_context, 1200)}",
                ]
            )

        ordered_parts = [f"## {key}\n{sections.get(key, '').strip()}" for key in self.order]
        system_prompt = self._join_parts(ordered_parts)
        self._validate_prompt_consistency(system_prompt)
        return PromptStackBuild(
            version=self.version,
            order=list(self.order),
            sections=sections,
            system_prompt=system_prompt,
        )


prompt_registry_v2 = PromptRegistryV2()

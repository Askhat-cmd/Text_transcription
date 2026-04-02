"""Prompt Stack v2 builder for Neo MindBot Phase 6."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from .config import config


PROMPT_STACK_VERSION = "2.0"
PROMPT_STACK_ORDER = (
    "AA_SAFETY",
    "A_STYLE_POLICY",
    "CORE_IDENTITY",
    "CONTEXT_MEMORY",
    "DIAGNOSTIC_CONTEXT",
    "RETRIEVED_CONTEXT",
    "TASK_INSTRUCTION",
)


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
            "sections": {k: len(v) for k, v in self.sections.items()},
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

    def _load_core_identity(self) -> str:
        try:
            return str(config.get_prompt("prompt_system_base")["text"]).strip()
        except Exception:
            return (
                "Ты помогаешь человеку уточнять внутренний процесс без давления, "
                "диагнозов и псевдо-уверенности."
            )

    def _build_style_policy(self, route: str, mode: str) -> str:
        normalized_route = (route or "").strip().lower()
        normalized_mode = (mode or "").strip().upper()
        if normalized_route == "safe_override":
            return (
                "Стиль: коротко, тепло, без поэтики и без директив. "
                "Не давай рискованные инструкции. Приоритет — стабилизация."
            )
        if normalized_route == "inform" or normalized_mode == "CLARIFICATION":
            return (
                "Стиль: нейтрально и структурно. "
                "Объясняй термины простыми словами, добавляй 1-2 примера."
            )
        if normalized_route == "regulate":
            return (
                "Стиль: бережно и замедляюще. "
                "Сначала контейнируй состояние, затем один небольшой шаг."
            )
        return (
            "Стиль: coaching-first, живой диалог, без пустых обобщений. "
            "Сохраняй ясность, конкретику и уважение к опыту пользователя."
        )

    def _build_memory_context(self, conversation_context: str) -> str:
        context = self._clip(conversation_context or "", 1200)
        if not context:
            return "История диалога: нет релевантного контекста."
        return f"История диалога (сжатая):\n{context}"

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
            "Диагностический контекст:\n"
            f"- interaction_mode: {interaction_mode}\n"
            f"- nervous_system_state: {nervous_state}\n"
            f"- request_function: {request_function}\n"
            f"- core_theme: {self._clip(core_theme, 180)}\n"
            f"- resolved_route: {route or 'reflect'}\n"
            f"- llm_mode: {mode or 'PRESENCE'}"
        )

    def _build_retrieved_context(self, blocks: List[object]) -> str:
        if not blocks:
            return "Контекст знаний: релевантные блоки не найдены."
        lines: List[str] = []
        for idx, block in enumerate(blocks[:6], start=1):
            title = str(getattr(block, "title", "") or getattr(block, "document_title", "")).strip()
            content = str(getattr(block, "summary", "") or getattr(block, "content", "")).strip()
            lines.append(f"[{idx}] {self._clip(title or 'Без названия', 90)}: {self._clip(content, 260)}")
        return "Контекст знаний:\n" + "\n".join(lines)

    def _build_task_instruction(
        self,
        *,
        route: str,
        mode: str,
        query: str,
        mode_prompt_override: Optional[str],
    ) -> str:
        route_text = route or "reflect"
        mode_text = mode or "PRESENCE"
        parts = [
            "Задача ответа:",
            f"- Маршрут: {route_text}",
            f"- Режим генерации: {mode_text}",
            f"- Ответь на запрос пользователя: {self._clip(query, 700)}",
            "- Не используй markdown-блоки кода и HTML-теги.",
            "- Не выдавай запрещающие/опасные директивы.",
        ]
        if mode_prompt_override:
            parts.append(f"- Доп. директива режима: {self._clip(mode_prompt_override, 260)}")
        return "\n".join(parts)

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
    ) -> PromptStackBuild:
        sections: Dict[str, str] = {
            "AA_SAFETY": (
                "Safety policy: не диагностируй, не лечи, не обещай гарантии. "
                "При признаках риска — приоритет безопасности и мягкая деэскалация."
            ),
            "A_STYLE_POLICY": self._build_style_policy(route=route, mode=mode),
            "CORE_IDENTITY": self._load_core_identity(),
            "CONTEXT_MEMORY": self._build_memory_context(conversation_context),
            "DIAGNOSTIC_CONTEXT": self._build_diagnostic_context(
                diagnostics=diagnostics, route=route, mode=mode
            ),
            "RETRIEVED_CONTEXT": self._build_retrieved_context(blocks),
            "TASK_INSTRUCTION": self._build_task_instruction(
                route=route,
                mode=mode,
                query=query,
                mode_prompt_override=mode_prompt_override,
            ),
        }
        if additional_system_context and additional_system_context.strip():
            sections["DIAGNOSTIC_CONTEXT"] = self._join_parts(
                [
                    sections["DIAGNOSTIC_CONTEXT"],
                    f"Дополнительный runtime-контекст:\n{self._clip(additional_system_context, 1200)}",
                ]
            )

        ordered_parts = [f"## {key}\n{sections.get(key, '').strip()}" for key in self.order]
        system_prompt = self._join_parts(ordered_parts)
        return PromptStackBuild(
            version=self.version,
            order=list(self.order),
            sections=sections,
            system_prompt=system_prompt,
        )


prompt_registry_v2 = PromptRegistryV2()


"""LLM adapter for multiagent agents.

Маршрутизирует вызовы между Chat Completions и Responses API
на основе model-family политики из config.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Optional

from ...config import config

logger = logging.getLogger(__name__)

_JSON_INSTRUCTION = (
    "Return ONLY valid JSON.\n"
    "Use double quotes for all keys and string values.\n"
    "No markdown.\n"
    "No comments.\n"
    "No trailing commas."
)
_SDK_CAPABILITY_LOG_KEYS: set[tuple[str, bool, bool, str]] = set()


@dataclass
class AgentLLMResult:
    """Normalized LLM result for multiagent agents."""

    text: str
    model: str
    api_mode: str  # "chat_completions" | "responses" | "chat_completions_compat"
    tokens_prompt: Optional[int] = None
    tokens_completion: Optional[int] = None
    tokens_total: Optional[int] = None
    raw_response: Optional[Any] = None


def _to_int(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _get_value(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def messages_to_input(messages: list[dict[str, str]]) -> str:
    """Convert chat-style messages into plain text input for Responses API."""

    parts: list[str] = []
    for message in messages:
        role = str(message.get("role", "user") or "user").upper()
        content = str(message.get("content", "") or "")
        parts.append(f"{role}:\n{content}")
    return "\n\n".join(parts)


def _extract_text_from_responses(response: Any) -> str:
    output_text = _get_value(response, "output_text", "")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    output = _get_value(response, "output", []) or []
    chunks: list[str] = []
    for item in output:
        item_type = _get_value(item, "type", "")
        if item_type == "message":
            content_items = _get_value(item, "content", []) or []
            for content in content_items:
                c_type = _get_value(content, "type", "")
                if c_type == "output_text":
                    text = _get_value(content, "text", "")
                    if text:
                        chunks.append(str(text))
        elif item_type == "output_text":
            text = _get_value(item, "text", "")
            if text:
                chunks.append(str(text))

    return "\n".join(chunk for chunk in chunks if chunk).strip()


def _extract_usage_chat(response: Any) -> tuple[Optional[int], Optional[int], Optional[int]]:
    usage = _get_value(response, "usage", None)
    prompt = _to_int(_get_value(usage, "prompt_tokens", None))
    completion = _to_int(_get_value(usage, "completion_tokens", None))
    total = _to_int(_get_value(usage, "total_tokens", None))
    if total is None and prompt is not None and completion is not None:
        total = prompt + completion
    return prompt, completion, total


def _extract_usage_responses(response: Any) -> tuple[Optional[int], Optional[int], Optional[int]]:
    usage = _get_value(response, "usage", None)
    prompt = _to_int(_get_value(usage, "input_tokens", None))
    completion = _to_int(_get_value(usage, "output_tokens", None))
    total = _to_int(_get_value(usage, "total_tokens", None))
    if total is None and prompt is not None and completion is not None:
        total = prompt + completion
    return prompt, completion, total


def _extract_text_from_chat(response: Any) -> str:
    return str(
        _get_value(
            _get_value(_get_value(response, "choices", [{}])[0], "message", {}),
            "content",
            "",
        )
        or ""
    ).strip()


def _client_has_path(client: Any, attr: str, nested_attr: str) -> bool:
    try:
        root = getattr(client, attr, None)
        nested = getattr(root, nested_attr, None)
        return callable(nested)
    except Exception:
        return False


def _detect_capabilities(client: Any) -> tuple[bool, bool]:
    has_responses = _client_has_path(client, "responses", "create")
    has_chat_completions = False
    try:
        chat = getattr(client, "chat", None)
        completions = getattr(chat, "completions", None)
        create = getattr(completions, "create", None)
        has_chat_completions = callable(create)
    except Exception:
        has_chat_completions = False
    return has_responses, has_chat_completions


def _log_capabilities_once(
    *,
    model: str,
    has_responses: bool,
    has_chat_completions: bool,
    selected_mode: str,
) -> None:
    key = (str(model), bool(has_responses), bool(has_chat_completions), str(selected_mode))
    if key in _SDK_CAPABILITY_LOG_KEYS:
        return
    _SDK_CAPABILITY_LOG_KEYS.add(key)
    logger.info(
        "[AGENT_LLM] sdk_capabilities has_responses=%s has_chat_completions=%s model=%s selected_mode=%s",
        has_responses,
        has_chat_completions,
        model,
        selected_mode,
    )


def _append_json_instruction(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    if not messages:
        return [{"role": "user", "content": _JSON_INSTRUCTION}]
    patched = [dict(msg) for msg in messages]
    last = dict(patched[-1])
    content = str(last.get("content", "") or "")
    if _JSON_INSTRUCTION not in content:
        content = f"{content}\n\n{_JSON_INSTRUCTION}".strip()
    last["content"] = content
    patched[-1] = last
    return patched


async def _call_chat_with_compat(
    *,
    client: Any,
    request_kwargs: dict[str, Any],
) -> Any:
    try:
        return await client.chat.completions.create(**request_kwargs)
    except TypeError as exc:
        # Some fake/legacy clients don't accept response_format kwarg.
        fallback_kwargs = dict(request_kwargs)
        retried = False
        err_text = str(exc)
        if "response_format" in fallback_kwargs and "response_format" in err_text:
            fallback_kwargs.pop("response_format", None)
            retried = True
        # Older SDK chat.completions may reject max_completion_tokens.
        # In compat mode drop the limit instead of sending unsupported max_tokens
        # for reasoning models (server can reject max_tokens for gpt-5 family).
        if (
            "max_completion_tokens" in fallback_kwargs
            and "max_completion_tokens" in err_text
        ):
            fallback_kwargs.pop("max_completion_tokens", None)
            retried = True
        if not retried:
            raise
        return await client.chat.completions.create(**fallback_kwargs)


async def create_agent_completion(
    *,
    client: Any,
    model: str,
    messages: list[dict[str, str]],
    temperature: float | None = None,
    max_tokens: int | None = None,
    timeout: float | None = None,
    response_format: dict | None = None,
    require_json: bool = False,
) -> AgentLLMResult:
    """Execute model call with model-family-aware API routing."""
    has_responses, has_chat_completions = _detect_capabilities(client)

    if not has_responses and not has_chat_completions:
        raise RuntimeError("OpenAI client has neither responses.create nor chat.completions.create")

    if config.supports_custom_temperature(model):
        token_param = config.get_token_param_name(model)
        request_kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
        }
        if max_tokens is not None:
            request_kwargs[token_param] = max_tokens
        if timeout is not None:
            request_kwargs["timeout"] = timeout
        if response_format is not None:
            request_kwargs["response_format"] = response_format
        if temperature is not None:
            request_kwargs["temperature"] = float(temperature)

        if not has_chat_completions:
            raise RuntimeError("OpenAI client has neither responses.create nor chat.completions.create")
        _log_capabilities_once(
            model=model,
            has_responses=has_responses,
            has_chat_completions=has_chat_completions,
            selected_mode="chat_completions",
        )
        response = await _call_chat_with_compat(client=client, request_kwargs=request_kwargs)
        text = _extract_text_from_chat(response)
        tokens_prompt, tokens_completion, tokens_total = _extract_usage_chat(response)
        return AgentLLMResult(
            text=text,
            model=model,
            api_mode="chat_completions",
            tokens_prompt=tokens_prompt,
            tokens_completion=tokens_completion,
            tokens_total=tokens_total,
            raw_response=response,
        )

    input_text = messages_to_input(messages)
    if require_json:
        input_text = f"{input_text}\n\n{_JSON_INSTRUCTION}"

    request_kwargs = {
        "model": model,
        "input": input_text,
    }
    if max_tokens is not None:
        request_kwargs["max_output_tokens"] = int(max_tokens)
    reasoning_effort = config.get_reasoning_effort(model)
    if reasoning_effort:
        request_kwargs["reasoning"] = {"effort": reasoning_effort}
    if timeout is not None:
        request_kwargs["timeout"] = timeout

    if has_responses:
        _log_capabilities_once(
            model=model,
            has_responses=has_responses,
            has_chat_completions=has_chat_completions,
            selected_mode="responses",
        )
        response = await client.responses.create(**request_kwargs)
        text = _extract_text_from_responses(response)
        tokens_prompt, tokens_completion, tokens_total = _extract_usage_responses(response)
        return AgentLLMResult(
            text=text,
            model=model,
            api_mode="responses",
            tokens_prompt=tokens_prompt,
            tokens_completion=tokens_completion,
            tokens_total=tokens_total,
            raw_response=response,
        )

    if not has_chat_completions:
        raise RuntimeError("OpenAI client has neither responses.create nor chat.completions.create")

    compat_messages = _append_json_instruction(messages) if require_json else list(messages)
    compat_kwargs: dict[str, Any] = {
        "model": model,
        "messages": compat_messages,
    }
    token_param = config.get_token_param_name(model)
    if max_tokens is not None:
        compat_kwargs[token_param] = int(max_tokens)
    if timeout is not None:
        compat_kwargs["timeout"] = timeout
    if response_format is not None:
        compat_kwargs["response_format"] = response_format
    elif require_json:
        compat_kwargs["response_format"] = {"type": "json_object"}

    _log_capabilities_once(
        model=model,
        has_responses=has_responses,
        has_chat_completions=has_chat_completions,
        selected_mode="chat_completions_compat",
    )
    compat_response = await _call_chat_with_compat(client=client, request_kwargs=compat_kwargs)
    compat_text = _extract_text_from_chat(compat_response)
    tokens_prompt, tokens_completion, tokens_total = _extract_usage_chat(compat_response)
    return AgentLLMResult(
        text=compat_text,
        model=model,
        api_mode="chat_completions_compat",
        tokens_prompt=tokens_prompt,
        tokens_completion=tokens_completion,
        tokens_total=tokens_total,
        raw_response=compat_response,
    )

"""LLM adapter for multiagent agents.

Маршрутизирует вызовы между Chat Completions и Responses API
на основе model-family политики из config.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from ...config import config


@dataclass
class AgentLLMResult:
    """Normalized LLM result for multiagent agents."""

    text: str
    model: str
    api_mode: str  # "chat_completions" | "responses"
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

        response = await client.chat.completions.create(**request_kwargs)
        text = str(_get_value(_get_value(_get_value(response, "choices", [{}])[0], "message", {}), "content", "") or "").strip()
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
        input_text = (
            f"{input_text}\n\n"
            "Return ONLY a valid JSON object. No markdown. No explanation."
        )

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

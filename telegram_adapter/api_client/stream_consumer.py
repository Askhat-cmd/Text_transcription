"""SSE consumer for Neo adaptive-stream endpoint."""

from __future__ import annotations

import json
from typing import Any

import httpx

from ..config import API_BASE_URL, API_KEY, STREAM_TIMEOUT_S


def _extract_data_payload(raw_line: str) -> str:
    # "data: ..." where exactly one formatting space after ":" is optional.
    payload = raw_line[len("data:") :]
    if payload.startswith(" "):
        payload = payload[1:]
    return payload


async def consume_adaptive_stream(
    query: str,
    user_id: str,
    session_id: str,
) -> str:
    """
    Consume SSE stream and return full assembled text.

    Telegram UX does not support token-by-token streaming directly, so we
    accumulate all chunks and send one formatted message.
    """
    url = f"{API_BASE_URL}/api/v1/questions/adaptive-stream"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY,
    }
    payload = {
        "query": query,
        "user_id": user_id,
        "session_id": session_id,
    }

    full_text = ""

    async with httpx.AsyncClient(timeout=STREAM_TIMEOUT_S) as client:
        async with client.stream("POST", url, headers=headers, json=payload) as response:
            response.raise_for_status()

            async for line in response.aiter_lines():
                if not line:
                    continue
                if line.startswith(":"):
                    continue
                if not line.startswith("data:"):
                    continue

                data = _extract_data_payload(line)
                done_marker = data.strip().lower()
                if done_marker in {"[done]", "done"}:
                    break

                try:
                    parsed: dict[str, Any] = json.loads(data)
                except json.JSONDecodeError:
                    full_text += data
                    continue

                if parsed.get("error"):
                    raise RuntimeError(str(parsed["error"]))

                delta = (
                    parsed.get("text")
                    or parsed.get("content")
                    or parsed.get("delta")
                    or parsed.get("token")
                    or ""
                )
                if isinstance(delta, str):
                    full_text += delta

                if bool(parsed.get("done")):
                    answer = parsed.get("answer")
                    if isinstance(answer, str) and answer.strip() and not full_text.strip():
                        full_text = answer
                    break

    return full_text.strip()


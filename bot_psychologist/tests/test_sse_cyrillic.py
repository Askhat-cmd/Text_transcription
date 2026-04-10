from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api import routes
from api.main import app

LONG_CYRILLIC_ANSWER = (
    "Осознанность — это практика намеренного внимания к текущему моменту. "
    "Она помогает наблюдать мысли, эмоции и ощущения без попытки их подавить. "
    "Регулярная практика снижает стресс и улучшает концентрацию. "
) * 8


def _fake_cyrillic_result(*_args, **_kwargs) -> dict:
    return {
        "status": "success",
        "answer": LONG_CYRILLIC_ANSWER,
        "processing_time_seconds": 0.05,
        "metadata": {"recommended_mode": "PRESENCE"},
    }


def test_cyrillic_tokens_reassemble_correctly(monkeypatch) -> None:
    monkeypatch.setattr(routes, "answer_question_adaptive", _fake_cyrillic_result)
    monkeypatch.setattr(routes.config, "ENABLE_STREAMING", True, raising=False)

    with TestClient(app, base_url="http://localhost") as client:
        response = client.post(
            "/api/v1/questions/adaptive-stream",
            json={"query": "Что такое осознанность?", "user_id": "test_cyr"},
            headers={"X-API-Key": "test-key-001"},
        )

    tokens_collected: list[str] = []
    done_answer = None

    for block in [chunk for chunk in response.text.split("\n\n") if chunk.strip()]:
        for line in block.splitlines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            raw = line.replace("data:", "", 1).strip()
            if not raw:
                continue
            payload = json.loads(raw)
            if "token" in payload:
                tokens_collected.append(payload["token"])
            if payload.get("done") is True:
                done_answer = payload.get("answer", "")

    reconstructed = "".join(tokens_collected).rstrip()

    assert done_answer is not None
    assert reconstructed == done_answer.rstrip()
    for token in tokens_collected:
        assert "\ufffd" not in token

from __future__ import annotations

from pathlib import Path

import pytest

from api import dependencies as deps
from bot_agent.config import config


@pytest.fixture()
def registration_db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "registration.db"
    monkeypatch.setattr(config, "BOT_DB_PATH", db_path, raising=False)

    for attr in [
        "_identity_repository",
        "_identity_service",
        "_conversation_repository",
        "_conversation_service",
        "_registration_repository",
        "_registration_service",
        "_link_attempt_guard",
        "_database_bootstrap",
        "_telegram_adapter_service",
        "_telegram_outbound_sender",
    ]:
        monkeypatch.setattr(deps, attr, None, raising=False)

    return db_path

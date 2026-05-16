from __future__ import annotations

from pathlib import Path


def test_botdb_docs_presence() -> None:
    required = [
        "Bot_data_base/docs/README.md",
        "Bot_data_base/docs/ARCHITECTURE.md",
        "Bot_data_base/docs/RUNBOOK.md",
        "Bot_data_base/docs/API_CONTRACTS.md",
        "Bot_data_base/docs/DATA_CONTRACTS.md",
        "Bot_data_base/docs/CHROMA_RECOVERY.md",
        "Bot_data_base/docs/SOURCE_HYGIENE.md",
        "Bot_data_base/docs/LEGACY_SD.md",
        "Bot_data_base/docs/PROJECT_STATE.md",
    ]
    missing = [path for path in required if not Path(path).exists()]
    assert missing == []

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADMIN_ROUTES = REPO_ROOT / "bot_psychologist/api/admin_routes.py"

MOJIBAKE_MARKERS = ("Р вЂ™", "Р Сџ", "РІР‚", "РІС™", "РІвЂќ")
TARGET_PATTERNS = (
    "_legacy_status_payload",
    "_compatibility_runtime_payload",
    "_runtime_agents_contract_payload",
    '"/runtime/effective"',
    '"/orchestrator/config"',
    '"/overview"',
)


def test_admin_runtime_contract_targeted_segments_have_no_mojibake() -> None:
    text = ADMIN_ROUTES.read_text(encoding="utf-8", errors="ignore")

    for pattern in TARGET_PATTERNS:
        idx = text.find(pattern)
        assert idx >= 0, f"pattern not found: {pattern}"
        segment = text[max(0, idx - 600): idx + 1200]
        for marker in MOJIBAKE_MARKERS:
            assert marker not in segment, f"mojibake marker '{marker}' found near {pattern}"

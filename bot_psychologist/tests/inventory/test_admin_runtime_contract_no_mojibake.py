from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADMIN_RUNTIME_COMPAT = REPO_ROOT / "bot_psychologist/api/admin_runtime_compat.py"
ADMIN_RUNTIME_EFFECTIVE = REPO_ROOT / "bot_psychologist/api/admin_runtime_effective_payload.py"
ADMIN_CONFIG_ROUTES = REPO_ROOT / "bot_psychologist/api/admin_config_routes.py"
ADMIN_AGENT_OPS = REPO_ROOT / "bot_psychologist/api/admin_agent_ops_routes.py"

MOJIBAKE_MARKERS = ("Р вЂ™", "Р Сџ", "РІР‚", "РІС™", "РІвЂќ")
TARGET_PATTERNS = {
    str(ADMIN_RUNTIME_COMPAT): (
        "_legacy_status_payload",
        "_compatibility_runtime_payload",
        "_runtime_agents_contract_payload",
    ),
    str(ADMIN_RUNTIME_EFFECTIVE): (),
    str(ADMIN_CONFIG_ROUTES): (
        '"/runtime/effective"',
    ),
    str(ADMIN_AGENT_OPS): (
        '"/orchestrator/config"',
        '"/overview"',
    ),
}


def test_admin_runtime_contract_targeted_segments_have_no_mojibake() -> None:
    for path_str, patterns in TARGET_PATTERNS.items():
        text = Path(path_str).read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            idx = text.find(pattern)
            assert idx >= 0, f"pattern not found: {pattern}"
            segment = text[max(0, idx - 600): idx + 1200]
            for marker in MOJIBAKE_MARKERS:
                assert marker not in segment, f"mojibake marker '{marker}' found near {pattern}"

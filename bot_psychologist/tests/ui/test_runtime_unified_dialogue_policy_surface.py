from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADMIN_PANEL_PATH = REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx"
ADMIN_ROUTES_PATH = REPO_ROOT / "bot_psychologist/api/admin_routes.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def test_runtime_effective_payload_exposes_unified_dialogue_policy_fields() -> None:
    text = _read(ADMIN_ROUTES_PATH)
    function_body = text.split("def _build_runtime_effective_payload", 1)[1].split("def ", 1)[0]
    assert '"version": str(effective_dialogue_policy.get("version", UNIFIED_DIALOGUE_POLICY_VERSION))' in function_body
    assert '"profile_preset": str(effective_dialogue_policy.get("profile_preset", profile_preset))' in function_body
    assert '"dialogue_act_resolver_enabled": True' in function_body
    assert '"last_offer_tracker_enabled": True' in function_body
    assert '"unanswered_question_tracker_enabled": True' in function_body
    assert '"style_state_enabled": True' in function_body
    assert '"broad_rollout_allowed": False' in function_body
    assert '"production_ready": False' in function_body


def test_runtime_tab_renders_unified_dialogue_policy_surface() -> None:
    text = _read(ADMIN_PANEL_PATH)
    assert "Unified Policy:" in text
    assert "active_profile_alias:" in text
    assert "profile_preset:" in text
    assert "final_answer_directive_role:" in text
    assert "writer_context_package_role:" in text
    assert "dialogue_act_resolver_enabled:" in text
    assert "last_offer_tracker_enabled:" in text
    assert "unanswered_question_tracker_enabled:" in text
    assert "style_state_enabled:" in text

from __future__ import annotations

from bot_agent.multiagent.planner_drift_monitor import (
    get_planner_drift_summary,
    record_planner_drift_check,
    reset_planner_drift_summary,
)


def test_monitor_counts_warning_and_critical() -> None:
    reset_planner_drift_summary()

    for _ in range(17):
        record_planner_drift_check("u1", {"status": "ok", "severity": "none", "flags": []})
    for _ in range(2):
        record_planner_drift_check(
            "u1",
            {"status": "warning", "severity": "medium", "flags": ["question_policy_violation"]},
        )
    record_planner_drift_check(
        "u1",
        {"status": "critical", "severity": "high", "flags": ["practice_policy_forbidden_violation"]},
    )

    summary = get_planner_drift_summary()
    assert summary["total"] == 20
    assert summary["ok_count"] == 17
    assert summary["warning_count"] == 2
    assert summary["critical_count"] == 1
    assert summary["by_flag"]["question_policy_violation"] == 2
    assert summary["by_flag"]["practice_policy_forbidden_violation"] == 1
    assert summary["threshold_status"] == "critical"


def test_monitor_summary_has_no_raw_text_or_full_answer() -> None:
    reset_planner_drift_summary()
    record_planner_drift_check(
        "u2",
        {
            "status": "warning",
            "severity": "medium",
            "flags": ["short_support_too_long"],
            "final_answer": "raw text should not be persisted",
            "user_message": "raw user text should not be persisted",
        },
    )

    summary = get_planner_drift_summary()
    assert "user_message" not in summary
    assert "final_answer" not in summary
    assert isinstance(summary.get("by_flag"), dict)

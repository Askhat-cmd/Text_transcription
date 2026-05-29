from __future__ import annotations

from collections import Counter, deque
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from .planner_drift_guard import PLANNER_DRIFT_GUARD_VERSION


DRIFT_MONITOR_WINDOW_SIZE = 100
_WARNING_RATE_THRESHOLD = 0.10
_CRITICAL_RATE_THRESHOLD = 0.03
_MIN_SAMPLE_FOR_RATES = 20


_history: deque[dict[str, Any]] = deque(maxlen=DRIFT_MONITOR_WINDOW_SIZE)
_history_lock = Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def reset_planner_drift_summary() -> None:
    with _history_lock:
        _history.clear()


def record_planner_drift_check(user_id: str, check: dict[str, Any]) -> None:
    item = {
        "timestamp": _now_iso(),
        "user_id_hash": f"u:{hash(str(user_id or '')) & 0xFFFFFFFF:08x}",
        "status": str(check.get("status", "ok") or "ok"),
        "severity": str(check.get("severity", "none") or "none"),
        "flags": [str(flag) for flag in list(check.get("flags", []) or []) if str(flag).strip()],
    }
    with _history_lock:
        _history.append(item)


def _counts() -> dict[str, Any]:
    with _history_lock:
        items = list(_history)

    total = len(items)
    ok_count = sum(1 for item in items if item.get("status") == "ok")
    warning_count = sum(1 for item in items if item.get("status") == "warning")
    critical_count = sum(1 for item in items if item.get("status") == "critical")

    by_flag_counter: Counter[str] = Counter()
    for item in items:
        for flag in list(item.get("flags", []) or []):
            by_flag_counter[str(flag)] += 1

    violations = warning_count + critical_count
    violation_rate = float(violations / total) if total else 0.0
    critical_rate = float(critical_count / total) if total else 0.0

    last_status = str(items[-1].get("status", "ok")) if items else "ok"
    last_flags = [str(flag) for flag in list(items[-1].get("flags", []) or [])] if items else []

    last5_has_medium = any(
        str(item.get("severity", "none")) == "medium" for item in items[-5:]
    )
    last3_has_high = any(
        str(item.get("severity", "none")) == "high" for item in items[-3:]
    )

    threshold_status = "ok"
    if (total >= _MIN_SAMPLE_FOR_RATES and critical_rate >= _CRITICAL_RATE_THRESHOLD) or last3_has_high:
        threshold_status = "critical"
    elif (total >= _MIN_SAMPLE_FOR_RATES and violation_rate >= _WARNING_RATE_THRESHOLD) or last5_has_medium:
        threshold_status = "warning"

    return {
        "version": PLANNER_DRIFT_GUARD_VERSION,
        "window_size": DRIFT_MONITOR_WINDOW_SIZE,
        "total": total,
        "ok_count": ok_count,
        "warning_count": warning_count,
        "critical_count": critical_count,
        "violation_rate": round(violation_rate, 4),
        "critical_rate": round(critical_rate, 4),
        "by_flag": dict(sorted(by_flag_counter.items())),
        "last_status": last_status,
        "last_flags": last_flags,
        "threshold_status": threshold_status,
        "thresholds": {
            "warning_violation_rate": _WARNING_RATE_THRESHOLD,
            "critical_rate": _CRITICAL_RATE_THRESHOLD,
            "min_samples": _MIN_SAMPLE_FOR_RATES,
            "recent_medium_window": 5,
            "recent_high_window": 3,
        },
    }


def get_planner_drift_summary() -> dict[str, Any]:
    return _counts()

"""One-time migration for runtime memory snapshot payloads -> v1.2 schema."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from bot_agent.config import config
from bot_agent.memory_v12 import build_snapshot_v12


STATE_MAP = {
    "curious": "window",
    "committed": "window",
    "calm": "window",
    "engaged": "window",
    "confused": "hyper",
    "overwhelmed": "hyper",
    "frustrated": "hyper",
    "anxious": "hyper",
    "detached": "hypo",
    "flat": "hypo",
    "numb": "hypo",
    "exhausted": "hypo",
}


def _migrate_snapshot_payload(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(snapshot, dict):
        return {}
    diagnostics = {}
    if isinstance(snapshot.get("diagnostics"), dict):
        diagnostics = dict(snapshot["diagnostics"])
    diagnostics.setdefault("nervous_system_state", snapshot.get("nervous_system_state"))
    diagnostics.setdefault("request_function", snapshot.get("request_function"))
    diagnostics.setdefault("core_theme", snapshot.get("core_theme"))
    if "user_state" in snapshot and not diagnostics.get("nervous_system_state"):
        diagnostics["nervous_system_state"] = STATE_MAP.get(str(snapshot.get("user_state")).lower(), "window")
    return build_snapshot_v12(
        diagnostics=diagnostics,
        route=(snapshot.get("_last_route") or snapshot.get("routing", {}).get("last_route") or "reflect"),
        engagement={
            "last_practice_channel": snapshot.get("last_practice_channel"),
            "active_track": snapshot.get("active_track"),
            "insights_log": snapshot.get("insights_log") or [],
        },
        summary_staleness=str(snapshot.get("_summary_staleness") or "missing"),
    )


def migrate_json_memory_cache() -> int:
    conversations_dir = Path(config.CACHE_DIR) / "conversations"
    if not conversations_dir.exists():
        return 0

    migrated = 0
    for path in conversations_dir.glob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        metadata = payload.get("metadata")
        if not isinstance(metadata, dict):
            continue
        source = (
            metadata.get("laststatesnapshot")
            or metadata.get("last_state_snapshot_v12")
            or metadata.get("last_state_snapshot_v11")
        )
        if not isinstance(source, dict):
            continue
        migrated_snapshot = _migrate_snapshot_payload(source)
        metadata["laststatesnapshot"] = migrated_snapshot
        metadata["last_state_snapshot_v12"] = migrated_snapshot
        metadata.pop("last_state_snapshot_v11", None)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        migrated += 1
    return migrated


if __name__ == "__main__":
    count = migrate_json_memory_cache()
    print(f"migrated_files={count}")

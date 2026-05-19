from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from tools.run_admin_browser_acceptance_hf2 import run_acceptance


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_visible_smoke(
    *,
    repo_root: str,
    admin_base_url: str,
    expected_source_id: str,
    expected_blocks: int,
) -> dict:
    acceptance = run_acceptance(
        repo_root=repo_root,
        admin_base_url=admin_base_url,
        expected_source_id=expected_source_id,
        expected_blocks=expected_blocks,
    )
    return {
        "schema_version": "admin_browser_visible_smoke_hf2_v1",
        "generated_at": _utc_now_iso(),
        "admin_base_url": admin_base_url,
        "dashboard_visible": bool(acceptance.get("dashboard_page_http_200")),
        "dashboard_chroma_status": acceptance.get("dashboard_chroma_status"),
        "dashboard_chroma_count": acceptance.get("dashboard_chroma_count"),
        "dashboard_blocks_count": acceptance.get("dashboard_chroma_count"),
        "registry_page_http_200": bool(acceptance.get("registry_page_http_200")),
        "registry_stats_http_200": bool(acceptance.get("registry_stats_http_200")),
        "registry_error_banner_absent": not bool(acceptance.get("registry_global_error_http_500")),
        "focus_source_visible": bool(acceptance.get("focus_source_visible")),
        "focus_source_protected": bool(acceptance.get("focus_source_protected")),
        "issues": list(acceptance.get("issues") or []),
        "runtime_fallback_used": bool(acceptance.get("runtime_fallback_used")),
        "primary_base_url": acceptance.get("primary_base_url"),
        "effective_base_url": acceptance.get("effective_base_url"),
        "admin_browser_visible_smoke_passed": bool(acceptance.get("admin_browser_acceptance_passed")),
        "raw_acceptance": acceptance,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="HF2 admin browser visible smoke")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--admin-base-url", default="http://127.0.0.1:8003")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--expected-source-id", default="123__кузница_духа")
    parser.add_argument("--expected-blocks", type=int, default=247)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    payload = run_visible_smoke(
        repo_root=str(args.repo_root),
        admin_base_url=str(args.admin_base_url),
        expected_source_id=str(args.expected_source_id),
        expected_blocks=int(args.expected_blocks),
    )
    out_path = Path(args.output_dir).resolve() / "admin_browser_visible_smoke.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if args.strict and not bool(payload.get("admin_browser_visible_smoke_passed")):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

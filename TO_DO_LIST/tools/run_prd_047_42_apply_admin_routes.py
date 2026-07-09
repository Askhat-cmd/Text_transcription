from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys


RUNNER_REPO_ROOT = Path(__file__).resolve().parents[2]


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_report(path: Path, title: str, diffs: list[str]) -> None:
    lines = [f"# {title}", ""]
    if not diffs:
        lines.append("- verdict: clean")
        lines.append("- differences: 0")
    else:
        lines.append("- verdict: differences_found")
        lines.append(f"- differences: {len(diffs)}")
        lines.append("")
        for diff in diffs:
            lines.append(f"- {diff}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="PRD-047.42-APPLY admin routes snapshot runner")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Repository root to import bot_psychologist from",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    capture_parser = subparsers.add_parser("capture", help="Capture current admin route snapshot")
    capture_parser.add_argument("--output", required=True, type=Path)

    diff_parser = subparsers.add_parser("diff", help="Compare before/after snapshots")
    diff_parser.add_argument("--before", required=True, type=Path)
    diff_parser.add_argument("--after", required=True, type=Path)
    diff_parser.add_argument("--report", required=True, type=Path)

    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    bot_root = repo_root / "bot_psychologist"
    if str(bot_root) not in sys.path:
        sys.path.insert(0, str(bot_root))
    support_path = RUNNER_REPO_ROOT / "bot_psychologist" / "tests" / "contract" / "admin_route_snapshot_support.py"
    spec = importlib.util.spec_from_file_location("prd_047_42_apply_support", support_path)
    assert spec and spec.loader
    support_module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = support_module
    spec.loader.exec_module(support_module)
    SNAPSHOT_SCHEMA_VERSION = support_module.SNAPSHOT_SCHEMA_VERSION
    capture_admin_route_snapshot = support_module.capture_admin_route_snapshot
    compare_snapshots = support_module.compare_snapshots

    if args.command == "capture":
        snapshot = capture_admin_route_snapshot()
        snapshot["schema_version"] = SNAPSHOT_SCHEMA_VERSION
        _write_json(args.output, snapshot)
        print(f"captured {snapshot['route_case_count']} route cases -> {args.output}")
        return 0

    before = json.loads(args.before.read_text(encoding="utf-8"))
    after = json.loads(args.after.read_text(encoding="utf-8"))
    diffs = compare_snapshots(before, after)
    _write_report(args.report, "PRD-047.42-APPLY routes diff report", diffs)
    print(f"diffs={len(diffs)} -> {args.report}")
    return 1 if diffs else 0


if __name__ == "__main__":
    raise SystemExit(main())

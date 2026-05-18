from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parents[1]
BOT_PSYCHOLOGIST_ROOT = REPO_ROOT / "bot_psychologist"
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))

from tools.validate_prd_artifact_encoding import run as shared_run  # type: ignore  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Wrapper for project artifact encoding validator")
    parser.add_argument("--prd", required=True)
    parser.add_argument("--logs-dir", required=True)
    parser.add_argument("--reports-dir", default="TO_DO_LIST/reports")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--report-prd", default="")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--fixed-file", action="append", default=[])
    args = parser.parse_args()

    if not str(args.report_prd).strip():
        args.report_prd = str(args.prd)

    report = shared_run(args)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if str(report.get("final_status") or "") == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


CURRENT_DIR = Path(__file__).resolve().parent
BOT_ROOT = CURRENT_DIR.parent
REPO_ROOT = BOT_ROOT.parent

if str(BOT_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_ROOT))

from bot_agent.experiments.thin_spine_runner import run_prd_047_28_experiment


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cases-path",
        default=str(REPO_ROOT / "TO_DO_LIST" / "fixtures" / "PRD-047.28" / "thin_spine_cases_ru.jsonl"),
    )
    parser.add_argument("--variant", choices=["A_current", "B_thin", "C_thin_note", "all"], default="all")
    parser.add_argument("--model", default=None)
    parser.add_argument("--temperature", type=float, default=None)
    parser.add_argument("--max-tokens", type=int, default=900)
    parser.add_argument("--recent-turn-count", type=int, default=4)
    parser.add_argument("--include-kb", action="store_true", default=False)
    parser.add_argument("--include-live-turn-note", action="store_true", default=False)
    parser.add_argument(
        "--output-dir",
        default=str(REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.28"),
    )
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--force-mock", action="store_true")
    args = parser.parse_args(argv)

    summary = run_prd_047_28_experiment(
        cases_path=args.cases_path,
        variant=args.variant,
        model=args.model,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        recent_turn_count=args.recent_turn_count,
        include_kb=bool(args.include_kb),
        include_live_turn_note=bool(args.include_live_turn_note),
        output_dir=args.output_dir,
        debug=bool(args.debug),
        force_mock=bool(args.force_mock),
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

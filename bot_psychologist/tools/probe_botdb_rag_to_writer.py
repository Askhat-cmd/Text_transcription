from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[1]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))

from bot_agent.multiagent import creator_live_evidence_rag_repair as hf1


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict:
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    payload = hf1.probe_botdb_query(
        query=args.query,
        botdb_base_url=args.botdb_base_url,
    )
    _write_json(output_dir / "botdb_direct_query_probe.json", payload)
    _write_json(output_dir / "chroma_query_failure_probe.json", payload)
    return payload


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Probe BotDB query path for PRD-046.1.35-HF1")
    parser.add_argument("--query", required=True)
    parser.add_argument("--botdb-base-url", default="http://localhost:8003")
    parser.add_argument("--output-dir", default="TO_DO_LIST/logs/PRD-046.1.35-HF1")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    payload = run(args)
    print(json.dumps(payload, ensure_ascii=True, indent=2))
    return 0 if int(payload.get("botdb_http_status", 0)) == 200 else 2


if __name__ == "__main__":
    raise SystemExit(main())

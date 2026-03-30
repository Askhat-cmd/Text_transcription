#!/usr/bin/env python3
"""Safe rebuild of a parallel Chroma collection for embedding migration."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Rebuilds local parallel Chroma collection psychologist_<model> "
            "without touching existing collections."
        )
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Required safety switch. Rebuild is blocked without this flag.",
    )
    parser.add_argument(
        "--backup-tag",
        default="pre-migration",
        help="Backup tag to validate (expects backups/chroma_<tag>_*).",
    )
    parser.add_argument(
        "--collection-prefix",
        default="psychologist",
        help="Collection prefix, final name is <prefix>_<model_tag>.",
    )
    parser.add_argument(
        "--persist-path",
        default="",
        help="Optional local chroma path; default bot_psychologist/data/chroma_rebuild.",
    )
    args = parser.parse_args()

    from bot_agent.chroma_loader import chroma_loader

    result = chroma_loader.rebuild_parallel_collection(
        confirm=bool(args.confirm),
        backup_tag=str(args.backup_tag),
        collection_prefix=str(args.collection_prefix),
        persist_path=str(args.persist_path) or None,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

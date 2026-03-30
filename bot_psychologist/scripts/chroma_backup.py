#!/usr/bin/env python3
"""Create a timestamped backup copy of ChromaDB directory."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime
from pathlib import Path


def _resolve_chroma_path(explicit_path: str | None, project_root: Path) -> Path:
    if explicit_path:
        path = Path(explicit_path).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"Chroma path does not exist: {path}")
        return path

    env_path = os.getenv("CHROMA_DB_PATH")
    if env_path:
        path = Path(env_path).expanduser().resolve()
        if path.exists():
            return path

    candidates = [
        project_root / "Bot_data_base" / "data" / "chroma_db",
        project_root / "bot_psychologist" / "data" / "chroma_db",
        project_root / "data" / "chroma",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()

    raise FileNotFoundError(
        "Could not locate ChromaDB directory. "
        "Set CHROMA_DB_PATH or pass --source."
    )


def _count_files(path: Path) -> int:
    return sum(1 for p in path.rglob("*") if p.is_file())


def backup_chroma(tag: str, source_path: str | None = None) -> Path:
    script_path = Path(__file__).resolve()
    project_root = script_path.parents[2]
    source = _resolve_chroma_path(source_path, project_root)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_root = project_root / "backups"
    backup_root.mkdir(parents=True, exist_ok=True)
    backup_dir = backup_root / f"chroma_{tag}_{timestamp}"

    shutil.copytree(source, backup_dir)

    metadata = {
        "tag": tag,
        "timestamp": timestamp,
        "source": str(source),
        "backup_dir": str(backup_dir),
        "file_count": _count_files(backup_dir),
    }
    (backup_dir / "backup_meta.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"[OK] Backup saved: {backup_dir}")
    print(f"[INFO] Source: {source}")
    print(f"[INFO] Files: {metadata['file_count']}")
    return backup_dir


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create ChromaDB backup into backups/chroma_<tag>_<timestamp>/",
    )
    parser.add_argument(
        "--tag",
        required=True,
        help="Backup tag, e.g. pre-e5-migration",
    )
    parser.add_argument(
        "--source",
        default=None,
        help="Explicit path to ChromaDB directory. If omitted, auto-detection is used.",
    )
    args = parser.parse_args()

    backup_chroma(tag=args.tag, source_path=args.source)


if __name__ == "__main__":
    main()


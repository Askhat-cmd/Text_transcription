from __future__ import annotations

import json
import os
from datetime import datetime
from typing import List

from models.universal_block import UniversalBlock


class JSONExporter:
    """
    Экспортирует блоки в JSON формат совместимый с bot_psychologist.
    """

    def __init__(self, base_dir: str = "data/processed") -> None:
        self.base_dir = base_dir

    def export(self, blocks: List[UniversalBlock], source_id: str, source_type: str) -> str:
        source_type = source_type.lower()
        if source_type not in {"youtube", "book", "books"}:
            source_type = "book" if source_type == "books" else source_type
        subdir = "youtube" if source_type == "youtube" else "books"
        out_dir = os.path.join(self.base_dir, subdir)
        os.makedirs(out_dir, exist_ok=True)

        payload = {
            "schema_version": "bot_data_base_v1.0",
            "source_id": source_id,
            "source_type": "youtube" if source_type == "youtube" else "book",
            "generated_at": datetime.utcnow().isoformat(),
            "blocks_count": len(blocks),
            "blocks": [b.to_bot_format() for b in blocks],
        }

        path = os.path.join(out_dir, f"{source_id}_blocks.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return path

    def export_all_merged(self) -> str:
        merged_blocks = []
        for subdir in ("youtube", "books"):
            dir_path = os.path.join(self.base_dir, subdir)
            if not os.path.isdir(dir_path):
                continue
            for name in os.listdir(dir_path):
                if not name.endswith("_blocks.json"):
                    continue
                path = os.path.join(dir_path, name)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    merged_blocks.extend(data.get("blocks", []))
                except Exception:
                    continue

        payload = {
            "schema_version": "bot_data_base_v1.0",
            "generated_at": datetime.utcnow().isoformat(),
            "blocks_count": len(merged_blocks),
            "blocks": merged_blocks,
        }

        out_path = os.path.join(self.base_dir, "all_blocks_merged.json")
        os.makedirs(self.base_dir, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return out_path

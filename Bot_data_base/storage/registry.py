from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional, List, Dict
import json
import os
import uuid


@dataclass
class SourceRecord:
    source_id: str
    source_type: str  # "youtube" | "book"
    title: str
    author: str
    author_id: str
    language: str
    status: str  # "pending"|"processing"|"done"|"failed"
    added_at: str
    processed_at: Optional[str]
    blocks_count: int
    sd_distribution: Dict[str, int]
    file_paths: Dict[str, object]
    error_message: Optional[str]
    pipeline_version: str

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "SourceRecord":
        return SourceRecord(**data)


class SourceRegistry:
    def __init__(self, registry_path: str):
        self.registry_path = registry_path
        os.makedirs(os.path.dirname(registry_path) or ".", exist_ok=True)
        if not os.path.exists(self.registry_path):
            self._save([])

    def add_source(self, record: SourceRecord) -> None:
        records = self._load()
        records.append(record)
        self._save(records)

    def get_source(self, source_id: str) -> Optional[SourceRecord]:
        records = self._load()
        for rec in records:
            if rec.source_id == source_id:
                return rec
        return None

    def update_status(self, source_id: str, status: str, **kwargs) -> None:
        records = self._load()
        updated = False
        for i, rec in enumerate(records):
            if rec.source_id == source_id:
                data = rec.to_dict()
                data["status"] = status
                for key, value in kwargs.items():
                    if key in data:
                        data[key] = value
                records[i] = SourceRecord.from_dict(data)
                updated = True
                break
        if updated:
            self._save(records)

    def is_processed(self, source_id: str) -> bool:
        rec = self.get_source(source_id)
        return bool(rec and rec.status == "done")

    def list_all(self) -> List[SourceRecord]:
        return self._load()

    def get_statistics(self) -> dict:
        records = self._load()
        total_sources = len(records)
        total_blocks = sum(r.blocks_count for r in records)

        sd_distribution: Dict[str, int] = {}
        sources_by_type: Dict[str, int] = {}
        for r in records:
            sources_by_type[r.source_type] = sources_by_type.get(r.source_type, 0) + 1
            for k, v in (r.sd_distribution or {}).items():
                sd_distribution[k] = sd_distribution.get(k, 0) + int(v)

        return {
            "total_sources": total_sources,
            "total_blocks": total_blocks,
            "sd_distribution": sd_distribution,
            "sources_by_type": sources_by_type,
        }

    def delete_source(self, source_id: str) -> bool:
        records = self._load()
        new_records = [r for r in records if r.source_id != source_id]
        if len(new_records) == len(records):
            return False
        self._save(new_records)
        return True

    def _load(self) -> List[SourceRecord]:
        if not os.path.exists(self.registry_path):
            return []
        with open(self.registry_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return []
            data = json.loads(content)
        return [SourceRecord.from_dict(item) for item in data]

    def _save(self, records: List[SourceRecord]) -> None:
        data = [r.to_dict() for r in records]
        tmp_path = f"{self.registry_path}.{uuid.uuid4().hex}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self.registry_path)

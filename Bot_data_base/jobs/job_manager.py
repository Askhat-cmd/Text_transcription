from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, List, Dict
import asyncio
import uuid


@dataclass
class JobRecord:
    job_id: str
    source_type: str
    source_ref: str
    status: str
    progress: int
    current_stage: str
    created_at: str
    finished_at: Optional[str]
    error: Optional[str]
    result: Optional[dict]

    def to_dict(self) -> dict:
        return asdict(self)


class JobManager:
    def __init__(self):
        self._jobs: Dict[str, JobRecord] = {}
        self._lock = asyncio.Lock()

    async def create_job(self, source_type: str, source_ref: str) -> str:
        job_id = str(uuid.uuid4())
        record = JobRecord(
            job_id=job_id,
            source_type=source_type,
            source_ref=source_ref,
            status="queued",
            progress=0,
            current_stage="queued",
            created_at=datetime.utcnow().isoformat(),
            finished_at=None,
            error=None,
            result=None,
        )
        async with self._lock:
            self._jobs[job_id] = record
        return job_id

    async def update_job(
        self,
        job_id: str,
        status: str,
        progress: int,
        current_stage: str,
        **kwargs,
    ) -> None:
        async with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return
            data = record.to_dict()
            data.update(
                {
                    "status": status,
                    "progress": progress,
                    "current_stage": current_stage,
                }
            )
            for key, value in kwargs.items():
                if key in data:
                    data[key] = value
            self._jobs[job_id] = JobRecord(**data)

    async def get_job(self, job_id: str) -> Optional[JobRecord]:
        async with self._lock:
            return self._jobs.get(job_id)

    async def list_jobs(self, limit: int = 20) -> List[JobRecord]:
        async with self._lock:
            values = list(self._jobs.values())
        return values[-limit:]

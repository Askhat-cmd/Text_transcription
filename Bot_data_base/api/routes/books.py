import os
from fastapi import APIRouter, BackgroundTasks, File, UploadFile, Form

from api.schemas import JobResponse
from jobs.job_manager import JobManager
from pipeline_runner import PipelineRunner

router = APIRouter()

_job_manager = JobManager()
_runner: PipelineRunner | None = None


def _job_to_response(job) -> JobResponse:
    return JobResponse(
        job_id=job.job_id,
        status=job.status,
        progress=job.progress,
        current_stage=job.current_stage,
        created_at=job.created_at,
        finished_at=job.finished_at,
        error=job.error,
        result=job.result,
    )


@router.post("/book", response_model=JobResponse)
async def ingest_book(
    background_tasks: BackgroundTasks,
    author: str = Form(...),
    author_id: str = Form(...),
    book_title: str = Form(...),
    language: str = Form("ru"),
    file: UploadFile = File(...),
):
    runner = get_runner()
    temp_dir = "data/uploads/books"
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, file.filename)
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    job_id = await _job_manager.create_job("book", file.filename)

    async def _run():
        result = await runner.run_book(
            file_path=file_path,
            author=author,
            author_id=author_id,
            book_title=book_title,
            language=language,
            job_id=job_id,
        )
        await _job_manager.update_job(
            job_id=job_id,
            status=result.get("status", "done"),
            progress=100,
            current_stage=result.get("status", "done"),
            result=result,
        )

    background_tasks.add_task(_run)
    job = await _job_manager.get_job(job_id)
    return _job_to_response(job)


def get_job_manager() -> JobManager:
    return _job_manager


def get_runner() -> PipelineRunner:
    global _runner
    if _runner is None:
        _runner = PipelineRunner(config_path="config.yaml", job_manager=_job_manager)
    return _runner




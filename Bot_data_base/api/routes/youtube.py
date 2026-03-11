from fastapi import APIRouter, BackgroundTasks, HTTPException

from api.schemas import YouTubeIngestRequest, JobResponse
from ingestors.youtube_ingestor import YouTubeIngestor
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


@router.post("/youtube", response_model=JobResponse)
async def ingest_youtube(request: YouTubeIngestRequest, background_tasks: BackgroundTasks):
    runner = get_runner()
    ing = YouTubeIngestor()
    video_id = ing.extract_video_id(request.url)
    if not video_id:
        raise HTTPException(status_code=422, detail="Invalid YouTube URL")

    job_id = await _job_manager.create_job("youtube", request.url)

    async def _run():
        result = await runner.run_youtube(
            url=request.url,
            author=request.author,
            author_id=request.author_id,
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


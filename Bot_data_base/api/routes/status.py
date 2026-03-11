from fastapi import APIRouter, HTTPException

from api.routes.youtube import get_job_manager as get_job_manager_youtube
from api.routes.books import get_job_manager as get_job_manager_books

router = APIRouter()


@router.get("/{job_id}")
async def get_job_status(job_id: str):
    jm = get_job_manager_youtube()
    job = await jm.get_job(job_id)
    if not job:
        jm = get_job_manager_books()
        job = await jm.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_dict()


@router.get("/")
async def list_jobs():
    jm = get_job_manager_youtube()
    jobs = await jm.list_jobs(limit=20)
    return {"jobs": [j.to_dict() for j in jobs]}

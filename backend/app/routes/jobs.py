from fastapi import APIRouter, HTTPException

from ..logger import get_logger
from ..models import JobCreateRequest, JobStatusResponse
from ..services.job_runner import job_runner

router = APIRouter(prefix="/api/jobs", tags=["jobs"])
logger = get_logger()


@router.post("", response_model=dict)
async def create_job(payload: JobCreateRequest) -> dict:
    if not payload.files:
        logger.warning("Create job rejected: no files provided")
        raise HTTPException(status_code=400, detail="Select at least one file.")
    try:
        job_id = await job_runner.create_job(payload)
        return {"job_id": job_id}
    except ValueError as exc:
        logger.error("Create job failed | error=%s", str(exc))
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{job_id}/cancel", response_model=dict)
def cancel_job(job_id: str) -> dict:
    job_runner.cancel_job(job_id)
    return {"ok": True}


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_job(job_id: str) -> JobStatusResponse:
    try:
        summary = job_runner.get_summary(job_id)
        results = job_runner.get_results(job_id)
    except ValueError as exc:
        logger.error("Get job failed | job_id=%s | error=%s", job_id, str(exc))
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return JobStatusResponse(summary=summary, results=results)

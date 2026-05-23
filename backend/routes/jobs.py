import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from database import engine
from models import Job
from schemas import JobOut

router = APIRouter()


def get_session():
    with Session(engine) as session:
        yield session


@router.get("/jobs", response_model=list[JobOut])
def list_jobs(
    keyword: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    session: Session = Depends(get_session),
):
    jobs = session.exec(select(Job)).all()

    if keyword:
        kw = keyword.lower()
        jobs = [
            j for j in jobs
            if kw in j.title.lower() or (j.description and kw in j.description.lower())
        ]

    if location:
        loc = location.lower()
        jobs = [
            j for j in jobs
            if (j.city and loc in j.city.lower())
            or (j.state and loc in j.state.lower())
            or (j.suburb and loc in j.suburb.lower())
        ]

    return [_to_out(j) for j in jobs]


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: int, session: Session = Depends(get_session)):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _to_out(job)


def _to_out(j: Job) -> JobOut:
    return JobOut(
        id=j.id,
        seek_url=j.seek_url,
        title=j.title,
        company=j.company,
        description=j.description,
        state=j.state,
        city=j.city,
        suburb=j.suburb,
        salary_range=j.salary_range,
        listed_dates=json.loads(j.listed_dates),
        is_repost=j.is_repost,
    )

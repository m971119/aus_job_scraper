import json
from typing import Literal, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlmodel import Session, col, select
from database import engine
from models import Job
from schemas import JobOut, JobsPage

router = APIRouter()


def get_session():
    with Session(engine) as session:
        yield session


@router.get("/jobs", response_model=JobsPage)
def list_jobs(
    keyword: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    sort: Literal["latest", "oldest"] = Query("latest"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    session: Session = Depends(get_session),
):
    query = select(Job)

    if keyword:
        kw = f"%{keyword}%"
        query = query.where(
            or_(col(Job.title).ilike(kw), col(Job.description).ilike(kw))
        )

    if location:
        loc = f"%{location}%"
        query = query.where(
            or_(
                col(Job.city).ilike(loc),
                col(Job.state).ilike(loc),
                col(Job.suburb).ilike(loc),
            )
        )

    order = col(Job.latest_listing_date).desc() if sort == "latest" else col(Job.latest_listing_date).asc()
    query = query.order_by(order)

    all_jobs = session.exec(query).all()
    total = len(all_jobs)
    start = (page - 1) * page_size
    jobs = all_jobs[start : start + page_size]

    return JobsPage(items=[_to_out(j) for j in jobs], total=total, page=page, page_size=page_size)


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
        latest_listing_date=j.latest_listing_date,
        is_repost=j.is_repost,
    )

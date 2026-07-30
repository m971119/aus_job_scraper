import json
from typing import Literal, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlmodel import Session, col, select
from database import engine
from models import Job, JobTag, Tag
from schemas import JobOut, JobsPage, NotesUpdate, StatusUpdate, TagOut
from scraper import SEEK_BASE

router = APIRouter()


def get_session():
    with Session(engine) as session:
        yield session


@router.get("/jobs", response_model=JobsPage)
def list_jobs(
    keyword: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    include_tag: Optional[str] = Query(None),
    exclude_tag: Optional[str] = Query(None),
    is_repost: Literal["all", "originals", "reposts"] = Query("all"),
    visibility: Literal["visible", "hidden", "all"] = Query("visible"),
    status: Optional[str] = Query(None),
    not_saved: bool = Query(False),
    sort: Literal["latest", "oldest"] = Query("latest"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    session: Session = Depends(get_session),
):
    query = select(Job)
    if visibility == "visible":
        query = query.where(Job.is_hidden == False)  # noqa: E712
    elif visibility == "hidden":
        query = query.where(Job.is_hidden == True)  # noqa: E712

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

    include_tags = [t.strip() for t in include_tag.split(",") if t.strip()] if include_tag else []
    exclude_tags = [t.strip() for t in exclude_tag.split(",") if t.strip()] if exclude_tag else []

    if include_tags:
        include_subq = (
            select(JobTag.job_id)
            .join(Tag, JobTag.tag_id == Tag.id)
            .where(or_(*[Tag.name.ilike(t) for t in include_tags]))
        )
        query = query.where(Job.id.in_(include_subq))

    for exc in exclude_tags:
        exclude_subq = (
            select(JobTag)
            .join(Tag, JobTag.tag_id == Tag.id)
            .where(JobTag.job_id == Job.id)
            .where(Tag.name.ilike(exc))
        ).exists()
        query = query.where(~exclude_subq)

    if is_repost == "originals":
        query = query.where(Job.is_repost == False)  # noqa: E712
    elif is_repost == "reposts":
        query = query.where(Job.is_repost == True)  # noqa: E712

    if not_saved:
        query = query.where(Job.status != "SAVED")
    elif status:
        query = query.where(Job.status == status)

    total = session.exec(select(func.count()).select_from(query.subquery())).one()

    order = col(Job.latest_listing_date).desc() if sort == "latest" else col(Job.latest_listing_date).asc()
    jobs = session.exec(query.order_by(order).offset((page - 1) * page_size).limit(page_size)).all()

    return JobsPage(items=[_to_out(j, session) for j in jobs], total=total, page=page, page_size=page_size)


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: int, session: Session = Depends(get_session)):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _to_out(job, session)


@router.patch("/jobs/{job_id}/hide", response_model=JobOut)
def hide_job(job_id: int, session: Session = Depends(get_session)):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.is_hidden = True
    job.hide_reason = "USER"
    session.add(job)
    session.commit()
    session.refresh(job)
    return _to_out(job, session)


@router.patch("/jobs/{job_id}/unhide", response_model=JobOut)
def unhide_job(job_id: int, session: Session = Depends(get_session)):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.is_hidden = False
    session.add(job)
    session.commit()
    session.refresh(job)
    return _to_out(job, session)


@router.patch("/jobs/{job_id}/notes", response_model=JobOut)
def update_notes(job_id: int, body: NotesUpdate, session: Session = Depends(get_session)):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.notes = body.notes
    session.add(job)
    session.commit()
    session.refresh(job)
    return _to_out(job, session)


@router.patch("/jobs/{job_id}/status", response_model=JobOut)
def update_status(job_id: int, body: StatusUpdate, session: Session = Depends(get_session)):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = body.status
    session.add(job)
    session.commit()
    session.refresh(job)
    return _to_out(job, session)


def _get_job_tags(session: Session, job_id: int) -> list[TagOut]:
    rows = session.exec(select(Tag).join(JobTag).where(JobTag.job_id == job_id)).all()
    return [TagOut(id=t.id, name=t.name) for t in rows]


def _to_out(j: Job, session: Session) -> JobOut:
    return JobOut(
        id=j.id,
        seek_url=f"{SEEK_BASE}{j.seek_url}",
        seek_urls=[f"{SEEK_BASE}{p}" for p in json.loads(j.seek_urls or "[]")],
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
        is_hidden=j.is_hidden,
        status=j.status,
        notes=j.notes,
        hide_reason=j.hide_reason,
        tags=_get_job_tags(session, j.id),
    )

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from sqlmodel import Session, select
from database import engine
from models import Job, JobTag, Tag
from schemas import TagCreate, TagOut

router = APIRouter()


@router.get("/tags", response_model=list[TagOut])
def list_tags():
    with Session(engine) as s:
        return [TagOut(id=t.id, name=t.name) for t in s.exec(select(Tag)).all()]


@router.post("/tags", response_model=TagOut, status_code=201)
def create_tag(body: TagCreate):
    with Session(engine) as s:
        existing = s.exec(
            select(Tag).where(Tag.name.ilike(body.name))
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail="Tag already exists")
        tag = Tag(name=body.name)
        s.add(tag)
        s.commit()
        s.refresh(tag)
        return TagOut(id=tag.id, name=tag.name)


@router.post("/jobs/{job_id}/tags/{tag_id}", response_model=TagOut)
def apply_tag(job_id: int, tag_id: int):
    with Session(engine) as s:
        if not s.get(Job, job_id):
            raise HTTPException(status_code=404, detail="Job not found")
        tag = s.get(Tag, tag_id)
        if not tag:
            raise HTTPException(status_code=404, detail="Tag not found")
        existing = s.exec(
            select(JobTag).where(JobTag.job_id == job_id, JobTag.tag_id == tag_id)
        ).first()
        if not existing:
            s.add(JobTag(job_id=job_id, tag_id=tag_id))
            s.commit()
        return TagOut(id=tag.id, name=tag.name)


@router.delete("/jobs/{job_id}/tags/{tag_id}")
def remove_tag(job_id: int, tag_id: int):
    with Session(engine) as s:
        link = s.exec(
            select(JobTag).where(JobTag.job_id == job_id, JobTag.tag_id == tag_id)
        ).first()
        if not link:
            raise HTTPException(status_code=404, detail="Tag not applied to this job")
        s.delete(link)
        s.commit()
        return JSONResponse(status_code=200, content={"status": "removed"})

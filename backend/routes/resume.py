import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlmodel import Session, select
from database import engine
from models import ResumeVersion
from schemas import (
    ResumeVersionCreate,
    ResumeVersionMeta,
    ResumeVersionOut,
    ResumeVersionUpdate,
)

router = APIRouter()


def get_session():
    with Session(engine) as session:
        yield session


def seed_resume() -> None:
    path_str = os.environ.get("RESUME_INITIAL_PATH")
    if not path_str:
        return
    path = Path(path_str)
    if not path.is_file():
        return
    with Session(engine) as session:
        count = session.exec(select(func.count()).select_from(ResumeVersion)).one()
        if count > 0:
            return
        session.add(ResumeVersion(label="Initial", content=path.read_text(encoding="utf-8")))
        session.commit()


@router.get("/resume", response_model=ResumeVersionOut)
def get_current_resume(session: Session = Depends(get_session)):
    version = session.exec(select(ResumeVersion).order_by(ResumeVersion.id.desc())).first()
    if not version:
        raise HTTPException(status_code=404, detail="No resume found")
    return version


@router.get("/resume/versions", response_model=list[ResumeVersionMeta])
def list_versions(session: Session = Depends(get_session)):
    return session.exec(select(ResumeVersion).order_by(ResumeVersion.id.desc())).all()


@router.get("/resume/versions/{version_id}", response_model=ResumeVersionOut)
def get_version(version_id: int, session: Session = Depends(get_session)):
    version = session.get(ResumeVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    return version


@router.post("/resume/versions", response_model=ResumeVersionOut, status_code=201)
def create_version(body: ResumeVersionCreate, session: Session = Depends(get_session)):
    version = ResumeVersion(label=body.label, content=body.content)
    session.add(version)
    session.commit()
    session.refresh(version)
    return version


@router.put("/resume/versions/{version_id}", response_model=ResumeVersionOut)
def update_version(
    version_id: int,
    body: ResumeVersionUpdate,
    session: Session = Depends(get_session),
):
    version = session.get(ResumeVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    version.content = body.content
    session.add(version)
    session.commit()
    session.refresh(version)
    return version


@router.delete("/resume/versions/{version_id}", status_code=204)
def delete_version(version_id: int, session: Session = Depends(get_session)):
    count = session.exec(select(func.count()).select_from(ResumeVersion)).one()
    if count <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the only remaining version")
    version = session.get(ResumeVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    session.delete(version)
    session.commit()

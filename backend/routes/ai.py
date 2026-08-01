import json
from datetime import datetime, timezone
from typing import AsyncIterator

import litellm
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlmodel import Session, delete, select

from ai_config import MODELS, advisor_system, cover_letter_system
from database import engine
from models import CoverLetter, Conversation, Job, Message, ResumeVersion
from schemas import (
    AdvisorOut,
    ChatRequest,
    CoverLetterOut,
    CoverLetterUpdate,
    GenerateRequest,
    MessageOut,
    ModelInfo,
    ResumeVersionLink,
)

router = APIRouter()


def get_session():
    with Session(engine) as session:
        yield session


def _get_resume(session: Session, job: Job) -> ResumeVersion:
    """Return the resume version linked to the job, or the latest."""
    if job.resume_version_id:
        rv = session.get(ResumeVersion, job.resume_version_id)
        if rv:
            return rv
    rv = session.exec(select(ResumeVersion).order_by(ResumeVersion.id.desc())).first()
    if not rv:
        raise HTTPException(status_code=422, detail="No resume found")
    return rv


async def _stream_llm(messages: list[dict], model: str) -> AsyncIterator[str]:
    response = await litellm.acompletion(model=model, messages=messages, stream=True)
    async for chunk in response:
        delta = chunk.choices[0].delta.content or ""
        if delta:
            yield delta


@router.get("/models", response_model=list[ModelInfo])
def list_models():
    return MODELS


@router.patch("/jobs/{job_id}/resume-version", response_model=dict)
def link_resume_version(
    job_id: int,
    body: ResumeVersionLink,
    session: Session = Depends(get_session),
):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if body.resume_version_id is not None:
        if not session.get(ResumeVersion, body.resume_version_id):
            raise HTTPException(status_code=404, detail="Resume version not found")
    job.resume_version_id = body.resume_version_id
    session.add(job)
    session.commit()
    return {"resume_version_id": job.resume_version_id}


@router.get("/jobs/{job_id}/cover-letter", response_model=CoverLetterOut)
def get_cover_letter(job_id: int, session: Session = Depends(get_session)):
    cl = session.exec(select(CoverLetter).where(CoverLetter.job_id == job_id)).first()
    if not cl:
        raise HTTPException(status_code=404, detail="No cover letter found")
    msgs = session.exec(
        select(Message)
        .where(Message.conversation_id == cl.conversation_id)
        .order_by(Message.id)
    ).all()
    return CoverLetterOut(
        id=cl.id,
        job_id=cl.job_id,
        resume_version_id=cl.resume_version_id,
        content=cl.content,
        conversation_id=cl.conversation_id,
        messages=[MessageOut.model_validate(m) for m in msgs],
        updated_at=cl.updated_at,
    )


@router.post("/jobs/{job_id}/cover-letter/generate")
async def generate_cover_letter(job_id: int, body: GenerateRequest):
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        if not job.description:
            raise HTTPException(status_code=422, detail="Job has no description")
        resume = _get_resume(session, job)
        system_prompt = cover_letter_system(resume, job)

        cl = session.exec(select(CoverLetter).where(CoverLetter.job_id == job_id)).first()
        if cl:
            session.exec(delete(Message).where(Message.conversation_id == cl.conversation_id))
            conv = session.get(Conversation, cl.conversation_id)
            conv.resume_version_id = resume.id
            session.add(conv)
            session.commit()
            conv_id = conv.id
            cl_id = cl.id
        else:
            conv = Conversation(job_id=job_id, resume_version_id=resume.id, type="cover_letter")
            session.add(conv)
            session.flush()
            cl = CoverLetter(
                job_id=job_id,
                resume_version_id=resume.id,
                content="",
                conversation_id=conv.id,
            )
            session.add(cl)
            session.commit()
            conv_id = conv.id
            cl_id = cl.id

        user_content = "Write a cover letter for this role."
        session.add(Message(conversation_id=conv_id, role="user", content=user_content))
        session.commit()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    async def event_stream():
        full = []
        async for delta in _stream_llm(messages, body.model):
            full.append(delta)
            yield f"data: {json.dumps({'delta': delta})}\n\n"
        full_content = "".join(full)
        with Session(engine) as s:
            s.add(Message(conversation_id=conv_id, role="assistant", content=full_content))
            saved_cl = s.get(CoverLetter, cl_id)
            saved_cl.content = full_content
            saved_cl.updated_at = datetime.now(timezone.utc)
            s.add(saved_cl)
            s.commit()
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/jobs/{job_id}/cover-letter/chat")
async def chat_cover_letter(job_id: int, body: ChatRequest):
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        if not job.description:
            raise HTTPException(status_code=422, detail="Job has no description")
        cl = session.exec(select(CoverLetter).where(CoverLetter.job_id == job_id)).first()
        if not cl:
            raise HTTPException(status_code=404, detail="Generate a cover letter first")
        resume = session.get(ResumeVersion, cl.resume_version_id)
        if not resume:
            raise HTTPException(status_code=422, detail="Linked resume version no longer exists")
        system_prompt = cover_letter_system(resume, job)
        history = [
            {"role": m.role, "content": m.content}
            for m in session.exec(
                select(Message)
                .where(Message.conversation_id == cl.conversation_id)
                .order_by(Message.id)
            ).all()
        ]
        session.add(Message(conversation_id=cl.conversation_id, role="user", content=body.message))
        session.commit()
        conv_id = cl.conversation_id
        cl_id = cl.id

    messages = [{"role": "system", "content": system_prompt}]
    messages += history
    messages.append({"role": "user", "content": body.message})

    async def event_stream():
        full = []
        async for delta in _stream_llm(messages, body.model):
            full.append(delta)
            yield f"data: {json.dumps({'delta': delta})}\n\n"
        full_content = "".join(full)
        with Session(engine) as s:
            s.add(Message(conversation_id=conv_id, role="assistant", content=full_content))
            saved_cl = s.get(CoverLetter, cl_id)
            saved_cl.content = full_content
            saved_cl.updated_at = datetime.now(timezone.utc)
            s.add(saved_cl)
            s.commit()
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.patch("/jobs/{job_id}/cover-letter", response_model=CoverLetterOut)
def update_cover_letter(
    job_id: int,
    body: CoverLetterUpdate,
    session: Session = Depends(get_session),
):
    cl = session.exec(select(CoverLetter).where(CoverLetter.job_id == job_id)).first()
    if not cl:
        raise HTTPException(status_code=404, detail="No cover letter found")
    cl.content = body.content
    cl.updated_at = datetime.now(timezone.utc)
    session.add(cl)
    session.commit()
    session.refresh(cl)
    msgs = session.exec(
        select(Message)
        .where(Message.conversation_id == cl.conversation_id)
        .order_by(Message.id)
    ).all()
    return CoverLetterOut(
        id=cl.id,
        job_id=cl.job_id,
        resume_version_id=cl.resume_version_id,
        content=cl.content,
        conversation_id=cl.conversation_id,
        messages=[MessageOut.model_validate(m) for m in msgs],
        updated_at=cl.updated_at,
    )


@router.get("/jobs/{job_id}/advisor")
def get_advisor(job_id: int, session: Session = Depends(get_session)):
    conv = session.exec(
        select(Conversation)
        .where(Conversation.job_id == job_id, Conversation.type == "advisor")
        .order_by(Conversation.id.desc())
    ).first()
    if not conv:
        return None
    msgs = session.exec(
        select(Message).where(Message.conversation_id == conv.id).order_by(Message.id)
    ).all()
    return AdvisorOut(
        conversation_id=conv.id,
        messages=[MessageOut.model_validate(m) for m in msgs],
    )


@router.delete("/jobs/{job_id}/advisor/messages", status_code=204)
def clear_advisor_history(job_id: int, session: Session = Depends(get_session)):
    conv = session.exec(
        select(Conversation)
        .where(Conversation.job_id == job_id, Conversation.type == "advisor")
        .order_by(Conversation.id.desc())
    ).first()
    if conv:
        session.exec(delete(Message).where(Message.conversation_id == conv.id))
        session.delete(conv)
        session.commit()


@router.post("/jobs/{job_id}/advisor/chat")
async def chat_advisor(job_id: int, body: ChatRequest):
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        if not job.description:
            raise HTTPException(status_code=422, detail="Job has no description")
        resume = _get_resume(session, job)
        system_prompt = advisor_system(resume, job)

        conv = session.exec(
            select(Conversation)
            .where(Conversation.job_id == job_id, Conversation.type == "advisor")
            .order_by(Conversation.id.desc())
        ).first()
        if not conv:
            conv = Conversation(job_id=job_id, resume_version_id=resume.id, type="advisor")
            session.add(conv)
            session.flush()
            session.commit()

        history = [
            {"role": m.role, "content": m.content}
            for m in session.exec(
                select(Message).where(Message.conversation_id == conv.id).order_by(Message.id)
            ).all()
        ]
        session.add(Message(conversation_id=conv.id, role="user", content=body.message))
        session.commit()
        conv_id = conv.id

    messages = [{"role": "system", "content": system_prompt}]
    messages += history
    messages.append({"role": "user", "content": body.message})

    async def event_stream():
        full = []
        async for delta in _stream_llm(messages, body.model):
            full.append(delta)
            yield f"data: {json.dumps({'delta': delta})}\n\n"
        full_content = "".join(full)
        with Session(engine) as s:
            s.add(Message(conversation_id=conv_id, role="assistant", content=full_content))
            s.commit()
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

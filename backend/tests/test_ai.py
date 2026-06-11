import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/test_ai.db")

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session
from main import app
from database import engine
from models import Job, ResumeVersion


@pytest.fixture(autouse=True)
def clean_db():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


@pytest.fixture()
def db():
    with Session(engine) as s:
        yield s


@pytest.fixture()
def job_with_description(db):
    job = Job(
        seek_url="https://seek.com.au/job/1",
        title="Software Engineer",
        company="Acme",
        description="We need a Python developer with FastAPI experience.",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@pytest.fixture()
def resume(db):
    rv = ResumeVersion(
        label="v1",
        content="<html><body>Python developer with 5 years experience.</body></html>",
    )
    db.add(rv)
    db.commit()
    db.refresh(rv)
    return rv


client = TestClient(app)


def _mock_stream(text: str):
    async def fake(*args, **kwargs):
        class Delta:
            content = text
        class Choice:
            delta = Delta()
        class Chunk:
            choices = [Choice()]
        class Stream:
            async def __aiter__(self):
                yield Chunk()
        return Stream()
    return fake


def test_list_models():
    resp = client.get("/api/models")
    assert resp.status_code == 200
    ids = [m["id"] for m in resp.json()]
    assert "gpt-4o-mini" in ids
    assert "gpt-4o" in ids
    assert "claude-sonnet-4-6" in ids


def test_link_resume_version(job_with_description, resume):
    resp = client.patch(
        f"/api/jobs/{job_with_description.id}/resume-version",
        json={"resume_version_id": resume.id},
    )
    assert resp.status_code == 200
    assert resp.json()["resume_version_id"] == resume.id


def test_link_resume_version_null(job_with_description, resume):
    client.patch(
        f"/api/jobs/{job_with_description.id}/resume-version",
        json={"resume_version_id": resume.id},
    )
    resp = client.patch(
        f"/api/jobs/{job_with_description.id}/resume-version",
        json={"resume_version_id": None},
    )
    assert resp.status_code == 200
    assert resp.json()["resume_version_id"] is None


def test_get_cover_letter_not_found(job_with_description):
    resp = client.get(f"/api/jobs/{job_with_description.id}/cover-letter")
    assert resp.status_code == 404


def test_generate_cover_letter_no_description(db):
    job = Job(seek_url="https://seek.com.au/job/2", title="Dev", description=None)
    db.add(job)
    db.commit()
    db.refresh(job)
    resp = client.post(
        f"/api/jobs/{job.id}/cover-letter/generate",
        json={"model": "gpt-4o-mini"},
    )
    assert resp.status_code == 422


def test_generate_cover_letter_creates_record(job_with_description, resume):
    with patch("routes.ai.litellm.acompletion", _mock_stream("Dear Hiring Manager, test letter.")):
        resp = client.post(
            f"/api/jobs/{job_with_description.id}/cover-letter/generate",
            json={"model": "gpt-4o-mini"},
        )
    assert resp.status_code == 200
    assert "data: " in resp.text
    assert "[DONE]" in resp.text

    get_resp = client.get(f"/api/jobs/{job_with_description.id}/cover-letter")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["content"] == "Dear Hiring Manager, test letter."
    assert len(data["messages"]) == 2  # user + assistant


def test_generate_cover_letter_is_idempotent(job_with_description, resume):
    with patch("routes.ai.litellm.acompletion", _mock_stream("First.")):
        client.post(
            f"/api/jobs/{job_with_description.id}/cover-letter/generate",
            json={"model": "gpt-4o-mini"},
        )
    with patch("routes.ai.litellm.acompletion", _mock_stream("Second.")):
        client.post(
            f"/api/jobs/{job_with_description.id}/cover-letter/generate",
            json={"model": "gpt-4o-mini"},
        )
    data = client.get(f"/api/jobs/{job_with_description.id}/cover-letter").json()
    assert data["content"] == "Second."
    assert len(data["messages"]) == 2  # old messages cleared, new pair only


def test_chat_cover_letter(job_with_description, resume):
    with patch("routes.ai.litellm.acompletion", _mock_stream("Initial letter.")):
        client.post(
            f"/api/jobs/{job_with_description.id}/cover-letter/generate",
            json={"model": "gpt-4o-mini"},
        )
    with patch("routes.ai.litellm.acompletion", _mock_stream("Revised letter.")):
        resp = client.post(
            f"/api/jobs/{job_with_description.id}/cover-letter/chat",
            json={"message": "Make it shorter", "model": "gpt-4o-mini"},
        )
    assert resp.status_code == 200
    assert "[DONE]" in resp.text
    data = client.get(f"/api/jobs/{job_with_description.id}/cover-letter").json()
    assert data["content"] == "Revised letter."
    assert len(data["messages"]) == 4  # generate user+assistant + chat user+assistant


def test_patch_cover_letter_manual_edit(job_with_description, resume):
    with patch("routes.ai.litellm.acompletion", _mock_stream("Original.")):
        client.post(
            f"/api/jobs/{job_with_description.id}/cover-letter/generate",
            json={"model": "gpt-4o-mini"},
        )
    resp = client.patch(
        f"/api/jobs/{job_with_description.id}/cover-letter",
        json={"content": "Manually edited."},
    )
    assert resp.status_code == 200
    assert resp.json()["content"] == "Manually edited."


def test_get_advisor_no_conversation(job_with_description):
    resp = client.get(f"/api/jobs/{job_with_description.id}/advisor")
    assert resp.status_code == 200
    assert resp.json() is None


def test_advisor_chat_creates_conversation(job_with_description, resume):
    with patch("routes.ai.litellm.acompletion", _mock_stream("• Missing: FastAPI")):
        resp = client.post(
            f"/api/jobs/{job_with_description.id}/advisor/chat",
            json={"message": "Please provide a structured analysis.", "model": "gpt-4o-mini"},
        )
    assert resp.status_code == 200
    assert "[DONE]" in resp.text

    data = client.get(f"/api/jobs/{job_with_description.id}/advisor").json()
    assert len(data["messages"]) == 2
    assert data["messages"][1]["content"] == "• Missing: FastAPI"


def test_advisor_no_description(db):
    job = Job(seek_url="https://seek.com.au/job/3", title="Dev", description=None)
    db.add(job)
    db.commit()
    db.refresh(job)
    resp = client.post(
        f"/api/jobs/{job.id}/advisor/chat",
        json={"message": "Analyse my resume", "model": "gpt-4o-mini"},
    )
    assert resp.status_code == 422

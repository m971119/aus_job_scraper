import json
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from main import app
from database import engine
from models import Job, Tag

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    from sqlmodel import SQLModel
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


def make_job(seek_url="https://seek.com.au/job/1", title="Dev") -> int:
    with Session(engine) as s:
        job = Job(
            seek_url=seek_url,
            title=title,
            listed_dates=json.dumps(["2026-05-26"]),
            latest_listing_date="2026-05-26",
        )
        s.add(job)
        s.commit()
        s.refresh(job)
        return job.id


def make_tag(name="Interested") -> int:
    with Session(engine) as s:
        tag = Tag(name=name)
        s.add(tag)
        s.commit()
        s.refresh(tag)
        return tag.id


def test_apply_tag_to_job():
    job_id = make_job()
    tag_id = make_tag()
    resp = client.post(f"/api/jobs/{job_id}/tags/{tag_id}")
    assert resp.status_code == 200
    detail = client.get(f"/api/jobs/{job_id}").json()
    assert any(t["id"] == tag_id for t in detail["tags"])


def test_apply_tag_idempotent():
    job_id = make_job()
    tag_id = make_tag()
    assert client.post(f"/api/jobs/{job_id}/tags/{tag_id}").status_code == 200
    assert client.post(f"/api/jobs/{job_id}/tags/{tag_id}").status_code == 200
    detail = client.get(f"/api/jobs/{job_id}").json()
    assert len([t for t in detail["tags"] if t["id"] == tag_id]) == 1


def test_apply_tag_wrong_job_returns_404():
    tag_id = make_tag()
    assert client.post(f"/api/jobs/9999/tags/{tag_id}").status_code == 404


def test_apply_tag_wrong_tag_returns_404():
    job_id = make_job()
    assert client.post(f"/api/jobs/{job_id}/tags/9999").status_code == 404


def test_remove_tag_from_job():
    job_id = make_job()
    tag_id = make_tag()
    client.post(f"/api/jobs/{job_id}/tags/{tag_id}")
    resp = client.delete(f"/api/jobs/{job_id}/tags/{tag_id}")
    assert resp.status_code == 200
    detail = client.get(f"/api/jobs/{job_id}").json()
    assert not any(t["id"] == tag_id for t in detail["tags"])


def test_remove_tag_does_not_delete_global_tag():
    job_id = make_job()
    tag_id = make_tag()
    client.post(f"/api/jobs/{job_id}/tags/{tag_id}")
    client.delete(f"/api/jobs/{job_id}/tags/{tag_id}")
    tags = client.get("/api/tags").json()
    assert any(t["id"] == tag_id for t in tags)


def test_remove_tag_not_applied_returns_404():
    job_id = make_job()
    tag_id = make_tag()
    assert client.delete(f"/api/jobs/{job_id}/tags/{tag_id}").status_code == 404


def test_job_detail_includes_tags():
    job_id = make_job()
    tag_id = make_tag("Python")
    client.post(f"/api/jobs/{job_id}/tags/{tag_id}")
    detail = client.get(f"/api/jobs/{job_id}").json()
    assert any(t["name"] == "Python" for t in detail["tags"])


def test_job_detail_tags_empty_by_default():
    job_id = make_job()
    detail = client.get(f"/api/jobs/{job_id}").json()
    assert detail["tags"] == []

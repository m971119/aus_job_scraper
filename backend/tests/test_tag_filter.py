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


def make_job(seek_url, title="Dev") -> int:
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


def make_tag(name) -> int:
    with Session(engine) as s:
        tag = Tag(name=name)
        s.add(tag)
        s.commit()
        s.refresh(tag)
        return tag.id


def test_filter_by_tag_returns_matching_jobs():
    job1 = make_job("https://seek.com.au/job/1")
    job2 = make_job("https://seek.com.au/job/2")
    tag_id = make_tag("Interested")
    client.post(f"/api/jobs/{job1}/tags/{tag_id}")

    resp = client.get("/api/jobs?include_tag=Interested")
    assert resp.status_code == 200
    ids = {j["id"] for j in resp.json()["items"]}
    assert job1 in ids
    assert job2 not in ids


def test_filter_by_tag_excludes_untagged_jobs():
    job1 = make_job("https://seek.com.au/job/1")
    make_job("https://seek.com.au/job/2")
    tag_id = make_tag("Python")
    client.post(f"/api/jobs/{job1}/tags/{tag_id}")

    resp = client.get("/api/jobs?include_tag=Python")
    assert resp.json()["total"] == 1


def test_filter_by_tag_case_insensitive():
    job_id = make_job("https://seek.com.au/job/1")
    tag_id = make_tag("Interested")
    client.post(f"/api/jobs/{job_id}/tags/{tag_id}")

    resp = client.get("/api/jobs?include_tag=interested")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_filter_by_unknown_tag_returns_empty():
    make_job("https://seek.com.au/job/1")
    resp = client.get("/api/jobs?include_tag=nonexistent")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_filter_by_tag_combined_with_keyword():
    job1 = make_job("https://seek.com.au/job/1", title="Senior Python Developer")
    job2 = make_job("https://seek.com.au/job/2", title="Junior Python Developer")
    tag_id = make_tag("Python")
    client.post(f"/api/jobs/{job1}/tags/{tag_id}")
    client.post(f"/api/jobs/{job2}/tags/{tag_id}")

    resp = client.get("/api/jobs?include_tag=Python&keyword=senior")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == job1

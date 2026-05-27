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


def make_job(seek_url: str, is_repost: bool = False) -> int:
    with Session(engine) as s:
        job = Job(
            seek_url=seek_url,
            title="Dev",
            listed_dates=json.dumps(["2026-05-26"]),
            latest_listing_date="2026-05-26",
            is_repost=is_repost,
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


# ---------------------------------------------------------------------------
# is_repost param values
# ---------------------------------------------------------------------------

def test_is_repost_defaults_to_all():
    make_job("url1", is_repost=False)
    make_job("url2", is_repost=True)
    resp = client.get("/api/jobs")
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


def test_is_repost_all_returns_both():
    make_job("url1", is_repost=False)
    make_job("url2", is_repost=True)
    resp = client.get("/api/jobs?is_repost=all")
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


def test_is_repost_originals_excludes_reposts():
    job1 = make_job("url1", is_repost=False)
    job2 = make_job("url2", is_repost=True)
    resp = client.get("/api/jobs?is_repost=originals")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == job1
    assert data["items"][0]["is_repost"] is False


def test_is_repost_reposts_excludes_originals():
    job1 = make_job("url1", is_repost=False)
    job2 = make_job("url2", is_repost=True)
    resp = client.get("/api/jobs?is_repost=reposts")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == job2
    assert data["items"][0]["is_repost"] is True


def test_is_repost_invalid_value_returns_422():
    resp = client.get("/api/jobs?is_repost=maybe")
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# edge cases
# ---------------------------------------------------------------------------

def test_is_repost_originals_returns_empty_when_all_are_reposts():
    make_job("url1", is_repost=True)
    make_job("url2", is_repost=True)
    resp = client.get("/api/jobs?is_repost=originals")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_is_repost_reposts_returns_empty_when_none_exist():
    make_job("url1", is_repost=False)
    make_job("url2", is_repost=False)
    resp = client.get("/api/jobs?is_repost=reposts")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_is_repost_hidden_jobs_never_appear():
    """is_hidden takes precedence over is_repost."""
    with Session(engine) as s:
        job = Job(
            seek_url="url1",
            title="Dev",
            listed_dates=json.dumps(["2026-05-26"]),
            latest_listing_date="2026-05-26",
            is_repost=True,
            is_hidden=True,
        )
        s.add(job)
        s.commit()

    resp = client.get("/api/jobs?is_repost=reposts")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


# ---------------------------------------------------------------------------
# combined with other filters
# ---------------------------------------------------------------------------

def test_is_repost_with_keyword():
    job1 = make_job("url1", is_repost=False)
    job2 = make_job("url2", is_repost=True)
    with Session(engine) as s:
        s.get(Job, job1).title = "Senior Engineer"
        s.get(Job, job2).title = "Senior Engineer"
        s.commit()

    resp = client.get("/api/jobs?is_repost=originals&keyword=senior")
    assert resp.status_code == 200
    ids = {j["id"] for j in resp.json()["items"]}
    assert ids == {job1}


def test_is_repost_with_exclude_tag():
    job1 = make_job("url1", is_repost=False)
    job2 = make_job("url2", is_repost=False)
    tag_id = make_tag("Rejected")
    client.post(f"/api/jobs/{job2}/tags/{tag_id}")

    resp = client.get("/api/jobs?is_repost=originals&exclude_tag=Rejected")
    assert resp.status_code == 200
    ids = {j["id"] for j in resp.json()["items"]}
    assert ids == {job1}


def test_is_repost_total_reflects_filtered_count():
    make_job("url1", is_repost=False)
    make_job("url2", is_repost=False)
    make_job("url3", is_repost=True)

    resp = client.get("/api/jobs?is_repost=originals&page_size=1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2       # filtered total, not 3
    assert len(data["items"]) == 1  # page_size honoured

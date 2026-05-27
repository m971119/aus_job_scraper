import json
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from main import app
from database import engine
from models import Job

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


def test_is_repost_default_returns_all_jobs():
    make_job("url1", is_repost=False)
    make_job("url2", is_repost=True)
    resp = client.get("/api/jobs")
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


def test_is_repost_all_returns_all_jobs():
    make_job("url1", is_repost=False)
    make_job("url2", is_repost=True)
    resp = client.get("/api/jobs?is_repost=all")
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


def test_is_repost_originals_returns_only_non_reposts():
    make_job("url1", is_repost=False)
    make_job("url2", is_repost=True)
    resp = client.get("/api/jobs?is_repost=originals")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["is_repost"] is False


def test_is_repost_reposts_returns_only_reposts():
    make_job("url1", is_repost=False)
    make_job("url2", is_repost=True)
    resp = client.get("/api/jobs?is_repost=reposts")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["is_repost"] is True


def test_is_repost_invalid_value_returns_422():
    resp = client.get("/api/jobs?is_repost=maybe")
    assert resp.status_code == 422

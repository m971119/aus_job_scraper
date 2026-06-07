import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/test_status.db")

import json
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from main import app
from database import engine
from models import Job


@pytest.fixture(autouse=True)
def clean_db():
    from sqlmodel import SQLModel
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


client = TestClient(app)


def make_job(**kwargs) -> Job:
    defaults = dict(
        seek_url="https://seek.com.au/job/1",
        title="Dev",
        listed_dates=json.dumps(["2026-05-24"]),
        latest_listing_date="2026-05-24",
    )
    return Job(**{**defaults, **kwargs})


def test_job_status_defaults_to_saved():
    with Session(engine) as s:
        j = make_job(seek_url="https://seek.com.au/job/1", title="Dev")
        s.add(j)
        s.commit()
        s.refresh(j)
        job_id = j.id

    resp = client.get(f"/api/jobs/{job_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "SAVED"


def test_update_status():
    with Session(engine) as s:
        j = make_job(seek_url="https://seek.com.au/job/1", title="Dev")
        s.add(j)
        s.commit()
        s.refresh(j)
        job_id = j.id

    resp = client.patch(f"/api/jobs/{job_id}/status", json={"status": "APPLIED"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "APPLIED"


def test_update_status_not_found():
    resp = client.patch("/api/jobs/99999/status", json={"status": "APPLIED"})
    assert resp.status_code == 404


def test_status_returned_in_job_list():
    with Session(engine) as s:
        j = make_job(seek_url="https://seek.com.au/job/1", title="Dev")
        j.status = "INTERVIEWING"
        s.add(j)
        s.commit()

    resp = client.get("/api/jobs")
    assert resp.json()["items"][0]["status"] == "INTERVIEWING"


def test_filter_by_exact_status():
    with Session(engine) as s:
        j1 = make_job(seek_url="https://seek.com.au/job/1", title="Applied Job")
        j1.status = "APPLIED"
        j2 = make_job(seek_url="https://seek.com.au/job/2", title="Saved Job")
        j2.status = "SAVED"
        s.add(j1)
        s.add(j2)
        s.commit()

    resp = client.get("/api/jobs?status=APPLIED")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Applied Job"


def test_filter_not_saved_excludes_saved_jobs():
    with Session(engine) as s:
        j1 = make_job(seek_url="https://seek.com.au/job/1", title="Applied Job")
        j1.status = "APPLIED"
        j2 = make_job(seek_url="https://seek.com.au/job/2", title="Saved Job")
        j2.status = "SAVED"
        j3 = make_job(seek_url="https://seek.com.au/job/3", title="Rejected Job")
        j3.status = "REJECTED"
        s.add(j1)
        s.add(j2)
        s.add(j3)
        s.commit()

    resp = client.get("/api/jobs?not_saved=true")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    titles = [j["title"] for j in data["items"]]
    assert "Saved Job" not in titles
    assert "Applied Job" in titles
    assert "Rejected Job" in titles

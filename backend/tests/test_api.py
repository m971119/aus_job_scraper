import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/test_api.db")

import json
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from main import app
from database import create_db, engine
from models import Job


@pytest.fixture(autouse=True)
def clean_db():
    from sqlmodel import SQLModel
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


client = TestClient(app)


def test_get_jobs_empty():
    resp = client.get("/api/jobs")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_jobs_with_keyword_filter():
    with Session(engine) as s:
        s.add(Job(
            seek_url="https://seek.com.au/job/999",
            title="Python Developer",
            city="Sydney",
            state="NSW",
            listed_dates=json.dumps(["2026-05-23"]),
        ))
        s.commit()

    resp = client.get("/api/jobs?keyword=python")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Python Developer"


def test_get_jobs_location_filter():
    with Session(engine) as s:
        s.add(Job(
            seek_url="https://seek.com.au/job/111",
            title="Data Engineer",
            city="Sydney",
            state="NSW",
            listed_dates=json.dumps(["2026-05-23"]),
        ))
        s.commit()

    resp = client.get("/api/jobs?location=Sydney")
    assert resp.status_code == 200
    data = resp.json()
    assert all("sydney" in (j["city"] or "").lower() for j in data)


def test_get_jobs_returns_listed_dates_as_list():
    with Session(engine) as s:
        s.add(Job(
            seek_url="https://seek.com.au/job/222",
            title="Frontend Dev",
            listed_dates=json.dumps(["2026-05-22", "2026-05-23"]),
            is_repost=True,
        ))
        s.commit()

    resp = client.get("/api/jobs")
    assert resp.status_code == 200
    data = resp.json()
    job = next(j for j in data if j["seek_url"] == "https://seek.com.au/job/222")
    assert isinstance(job["listed_dates"], list)
    assert len(job["listed_dates"]) == 2
    assert job["is_repost"] is True

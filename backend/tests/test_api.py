import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/test_api.db")

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


def test_get_jobs_empty():
    resp = client.get("/api/jobs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_get_jobs_with_keyword_filter():
    with Session(engine) as s:
        s.add(make_job(seek_url="https://seek.com.au/job/1", title="Python Developer", city="Sydney", state="NSW"))
        s.add(make_job(seek_url="https://seek.com.au/job/2", title="Java Engineer", city="Sydney", state="NSW"))
        s.commit()

    resp = client.get("/api/jobs?keyword=python")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Python Developer"


def test_get_jobs_location_filter():
    with Session(engine) as s:
        s.add(make_job(seek_url="https://seek.com.au/job/1", title="Dev", city="Sydney", state="NSW"))
        s.add(make_job(seek_url="https://seek.com.au/job/2", title="Dev", city="Melbourne", state="VIC"))
        s.commit()

    resp = client.get("/api/jobs?location=Sydney")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["city"] == "Sydney"


def test_get_jobs_sort_latest():
    with Session(engine) as s:
        s.add(make_job(seek_url="https://seek.com.au/job/1", title="Old", listed_dates=json.dumps(["2026-05-01"]), latest_listing_date="2026-05-01"))
        s.add(make_job(seek_url="https://seek.com.au/job/2", title="New", listed_dates=json.dumps(["2026-05-20"]), latest_listing_date="2026-05-20"))
        s.commit()

    resp = client.get("/api/jobs?sort=latest")
    data = resp.json()
    assert data["items"][0]["title"] == "New"
    assert data["items"][1]["title"] == "Old"


def test_get_jobs_pagination():
    with Session(engine) as s:
        for i in range(5):
            s.add(make_job(seek_url=f"https://seek.com.au/job/{i}", title=f"Job {i}"))
        s.commit()

    resp = client.get("/api/jobs?page=1&page_size=2")
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["page_size"] == 2

    resp2 = client.get("/api/jobs?page=3&page_size=2")
    assert len(resp2.json()["items"]) == 1


def test_get_jobs_returns_listed_dates_as_list():
    with Session(engine) as s:
        s.add(make_job(
            seek_url="https://seek.com.au/job/222",
            title="Frontend Dev",
            listed_dates=json.dumps(["2026-05-22", "2026-05-23"]),
            latest_listing_date="2026-05-23",
            is_repost=True,
        ))
        s.commit()

    resp = client.get("/api/jobs")
    data = resp.json()
    job = next(j for j in data["items"] if j["seek_url"] == "https://seek.com.au/job/222")
    assert isinstance(job["listed_dates"], list)
    assert len(job["listed_dates"]) == 2
    assert job["is_repost"] is True
    assert job["latest_listing_date"] == "2026-05-23"


def test_get_job_by_id():
    with Session(engine) as s:
        job = make_job(
            seek_url="https://seek.com.au/job/555",
            title="Backend Dev",
            company="Acme",
            state="VIC",
            city="Melbourne",
            description="Great role.",
        )
        s.add(job)
        s.commit()
        s.refresh(job)
        job_id = job.id

    resp = client.get(f"/api/jobs/{job_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Backend Dev"
    assert data["company"] == "Acme"
    assert data["description"] == "Great role."
    assert isinstance(data["listed_dates"], list)


def test_get_job_by_id_not_found():
    resp = client.get("/api/jobs/99999")
    assert resp.status_code == 404


def test_hide_job_excludes_from_list():
    with Session(engine) as s:
        s.add(make_job(seek_url="https://seek.com.au/job/1", title="Visible"))
        j = make_job(seek_url="https://seek.com.au/job/2", title="Hidden")
        s.add(j)
        s.commit()
        s.refresh(j)
        job_id = j.id

    resp = client.patch(f"/api/jobs/{job_id}/hide")
    assert resp.status_code == 200
    assert resp.json()["is_hidden"] is True

    list_resp = client.get("/api/jobs")
    titles = [j["title"] for j in list_resp.json()["items"]]
    assert "Visible" in titles
    assert "Hidden" not in titles


def test_hide_job_skipped_on_rescrape():
    with Session(engine) as s:
        j = Job(
            seek_url="https://seek.com.au/job/hidden",
            title="Old Job",
            listed_dates='["2026-05-01"]',
            latest_listing_date="2026-05-01",
            is_hidden=True,
        )
        s.add(j)
        s.commit()

    from schemas import ScrapedJob
    from unittest.mock import patch

    fake = [ScrapedJob(seek_url="https://seek.com.au/job/hidden", title="Old Job", listed_date="2026-05-24")]
    with patch("routes.scrape.scrape_seek", return_value=fake):
        resp = client.post("/api/scrape", json={"keywords": "x", "location": "y", "max_pages": 1})

    assert resp.status_code == 200
    data = resp.json()
    assert data["inserted"] == 0
    assert data["skipped_hidden"] == 1

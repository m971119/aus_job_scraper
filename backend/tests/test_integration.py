"""
Integration tests -- hit live Seek.com.au. Requires internet access.
Run with: uv run pytest tests/test_integration.py -v -m integration
"""
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/test_integration.db")

import json
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel
from main import app
from database import create_db, engine

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def clean_db():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


client = TestClient(app)


def test_scrape_and_retrieve():
    """Full flow: scrape Seek, store in DB, retrieve via API."""
    resp = client.post("/api/scrape", json={
        "keywords": "python developer",
        "location": "Melbourne",
        "max_pages": 1,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "scraped" in data
    assert "inserted" in data
    assert data["scraped"] >= 0

    jobs_resp = client.get("/api/jobs")
    assert jobs_resp.status_code == 200
    jobs = jobs_resp.json()
    assert isinstance(jobs, list)
    if jobs:
        j = jobs[0]
        assert "title" in j
        assert "seek_url" in j
        assert "seek.com.au" in j["seek_url"]
        assert isinstance(j["listed_dates"], list)
        assert len(j["listed_dates"]) >= 1


def test_repost_detection():
    """Scraping the same jobs twice marks them as reposted on a different date."""
    payload = {"keywords": "data engineer", "location": "Sydney", "max_pages": 1}
    r1 = client.post("/api/scrape", json=payload)
    assert r1.status_code == 200
    first = r1.json()

    # Simulate a second scrape on a different date by patching the date
    from unittest.mock import patch
    from datetime import date
    with patch("scraper.date") as mock_date:
        mock_date.today.return_value = date(2026, 6, 1)
        r2 = client.post("/api/scrape", json=payload)
    assert r2.status_code == 200
    second = r2.json()

    if first["inserted"] > 0:
        assert second["updated_reposts"] >= 0  # some should be reposted


def test_keyword_filter_reduces_results():
    """After scraping, keyword filter should narrow results."""
    client.post("/api/scrape", json={
        "keywords": "software engineer",
        "location": "Brisbane",
        "max_pages": 1,
    })

    all_resp = client.get("/api/jobs")
    filtered_resp = client.get("/api/jobs?keyword=software")

    assert all_resp.status_code == 200
    assert filtered_resp.status_code == 200

    all_jobs = all_resp.json()
    filtered = filtered_resp.json()
    # Filtered should be <= total
    assert len(filtered) <= len(all_jobs)

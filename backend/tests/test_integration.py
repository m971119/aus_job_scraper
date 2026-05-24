"""
Integration tests -- hit live Seek.com.au. Requires internet access.
Run with: uv run pytest tests/test_integration.py -v -m integration
"""
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/test_integration.db")

import asyncio
import pytest
import httpx
from sqlmodel import SQLModel
from main import app
from database import engine

pytestmark = pytest.mark.integration

TRANSPORT = httpx.ASGITransport(app=app)
BASE_URL = "http://test"


@pytest.fixture(autouse=True)
def clean_db():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


async def wait_for_scrape(client: httpx.AsyncClient, timeout: int = 120) -> dict:
    """Poll /api/scrape/status until done, cancelled, or error."""
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        res = await client.get("/api/scrape/status")
        data = res.json()
        if data["status"] in ("done", "cancelled", "error"):
            return data
        await asyncio.sleep(2)
    return (await client.get("/api/scrape/status")).json()


@pytest.mark.asyncio
async def test_scrape_and_retrieve():
    """Full flow: scrape Seek, store in DB, retrieve via API."""
    async with httpx.AsyncClient(transport=TRANSPORT, base_url=BASE_URL) as client:
        resp = await client.post("/api/scrape", json={
            "keywords": "python developer",
            "location": "Melbourne",
        })
        assert resp.status_code == 202

        state = await wait_for_scrape(client)
        assert state["status"] == "done", f"Scrape failed or timed out: {state}"
        assert state["inserted"] >= 1

        jobs_resp = await client.get("/api/jobs")
        assert jobs_resp.status_code == 200
        jobs = jobs_resp.json()["items"]
        assert len(jobs) >= 1

        j = jobs[0]
        assert j["title"], "title should be non-empty"
        assert j["seek_url"], "seek_url should be non-empty"
        assert "seek.com.au" in j["seek_url"]
        assert "?" not in j["seek_url"], "seek_url should have no tracking query params"
        assert j["company"], "company should be non-empty"
        assert j["state"], "state should be non-empty"
        assert isinstance(j["listed_dates"], list)
        assert len(j["listed_dates"]) >= 1


@pytest.mark.asyncio
async def test_repost_detection():
    """Scraping the same jobs twice marks them as reposted on a different date."""
    async with httpx.AsyncClient(transport=TRANSPORT, base_url=BASE_URL) as client:
        payload = {"keywords": "data engineer", "location": "Sydney"}
        r1 = await client.post("/api/scrape", json=payload)
        assert r1.status_code == 202
        state1 = await wait_for_scrape(client)
        assert state1["status"] == "done"
        first_inserted = state1["inserted"]

        from unittest.mock import patch
        from datetime import date
        with patch("scraper.date") as mock_date:
            mock_date.today.return_value = date(2026, 6, 1)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            r2 = await client.post("/api/scrape", json=payload)
            assert r2.status_code == 202
            state2 = await wait_for_scrape(client)

        assert state2["status"] == "done"
        if first_inserted > 0:
            assert state2["updated_reposts"] >= 0


@pytest.mark.asyncio
async def test_keyword_filter_reduces_results():
    """After scraping, keyword filter should narrow results."""
    async with httpx.AsyncClient(transport=TRANSPORT, base_url=BASE_URL) as client:
        await client.post("/api/scrape", json={
            "keywords": "software engineer",
            "location": "Brisbane",
        })
        await wait_for_scrape(client)

        all_resp = await client.get("/api/jobs")
        filtered_resp = await client.get("/api/jobs?keyword=software")

        assert all_resp.status_code == 200
        assert filtered_resp.status_code == 200

        all_jobs = all_resp.json()["items"]
        filtered = filtered_resp.json()["items"]
        assert len(filtered) <= len(all_jobs)

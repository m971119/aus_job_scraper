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


def make_job(seek_url, title="Dev", is_repost=False) -> int:
    with Session(engine) as s:
        job = Job(
            seek_url=seek_url,
            title=title,
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


def tag_job(job_id: int, tag_id: int):
    client.post(f"/api/jobs/{job_id}/tags/{tag_id}")


# ---------------------------------------------------------------------------
# include_tag — single
# ---------------------------------------------------------------------------

def test_include_tag_returns_only_tagged_job():
    job1 = make_job("url1")
    job2 = make_job("url2")
    tag_id = make_tag("Interested")
    tag_job(job1, tag_id)

    resp = client.get("/api/jobs?include_tag=Interested")
    assert resp.status_code == 200
    ids = {j["id"] for j in resp.json()["items"]}
    assert ids == {job1}
    assert job2 not in ids


def test_include_tag_case_insensitive():
    job_id = make_job("url1")
    tag_id = make_tag("Interested")
    tag_job(job_id, tag_id)

    resp = client.get("/api/jobs?include_tag=interested")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_include_tag_unknown_returns_empty():
    make_job("url1")
    resp = client.get("/api/jobs?include_tag=nonexistent")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_include_tag_with_keyword():
    job1 = make_job("url1", title="Senior Python Developer")
    job2 = make_job("url2", title="Junior Python Developer")
    tag_id = make_tag("Python")
    tag_job(job1, tag_id)
    tag_job(job2, tag_id)

    resp = client.get("/api/jobs?include_tag=Python&keyword=senior")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == job1


# ---------------------------------------------------------------------------
# include_tag — multiple (OR logic)
# ---------------------------------------------------------------------------

def test_multi_include_tags_returns_union():
    job1 = make_job("url1", title="Python Dev")
    job2 = make_job("url2", title="React Dev")
    job3 = make_job("url3", title="Java Dev")
    python_id = make_tag("Python")
    react_id = make_tag("React")
    tag_job(job1, python_id)
    tag_job(job2, react_id)

    resp = client.get("/api/jobs?include_tag=Python&include_tag=React")
    assert resp.status_code == 200
    ids = {j["id"] for j in resp.json()["items"]}
    assert ids == {job1, job2}
    assert job3 not in ids


def test_multi_include_tags_no_duplicate_rows_when_job_has_both():
    job1 = make_job("url1")
    python_id = make_tag("Python")
    react_id = make_tag("React")
    tag_job(job1, python_id)
    tag_job(job1, react_id)

    resp = client.get("/api/jobs?include_tag=Python&include_tag=React")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert len(resp.json()["items"]) == 1


def test_multi_include_tags_all_unknown_returns_empty():
    make_job("url1")
    resp = client.get("/api/jobs?include_tag=Foo&include_tag=Bar")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


# ---------------------------------------------------------------------------
# exclude_tag — single
# ---------------------------------------------------------------------------

def test_exclude_tag_removes_tagged_job():
    job1 = make_job("url1")
    job2 = make_job("url2")
    tag_id = make_tag("Rejected")
    tag_job(job2, tag_id)

    resp = client.get("/api/jobs?exclude_tag=Rejected")
    assert resp.status_code == 200
    ids = {j["id"] for j in resp.json()["items"]}
    assert ids == {job1}


def test_exclude_tag_case_insensitive():
    job1 = make_job("url1")
    job2 = make_job("url2")
    tag_id = make_tag("Rejected")
    tag_job(job2, tag_id)

    resp = client.get("/api/jobs?exclude_tag=rejected")
    assert resp.status_code == 200
    ids = {j["id"] for j in resp.json()["items"]}
    assert ids == {job1}


def test_exclude_tag_unknown_returns_all_jobs():
    make_job("url1")
    make_job("url2")
    resp = client.get("/api/jobs?exclude_tag=nonexistent")
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


# ---------------------------------------------------------------------------
# exclude_tag — multiple
# ---------------------------------------------------------------------------

def test_multi_exclude_tags_excludes_any_match():
    job1 = make_job("url1")
    job2 = make_job("url2")
    job3 = make_job("url3")
    rejected_id = make_tag("Rejected")
    not_interested_id = make_tag("NotInterested")
    tag_job(job2, rejected_id)
    tag_job(job3, not_interested_id)

    resp = client.get("/api/jobs?exclude_tag=Rejected&exclude_tag=NotInterested")
    assert resp.status_code == 200
    ids = {j["id"] for j in resp.json()["items"]}
    assert ids == {job1}


# ---------------------------------------------------------------------------
# include + exclude combinations
# ---------------------------------------------------------------------------

def test_include_and_exclude_different_tags():
    job1 = make_job("url1")   # Python only → kept
    job2 = make_job("url2")   # Python + Rejected → excluded
    job3 = make_job("url3")   # no tags → not in include results
    python_id = make_tag("Python")
    rejected_id = make_tag("Rejected")
    tag_job(job1, python_id)
    tag_job(job2, python_id)
    tag_job(job2, rejected_id)

    resp = client.get("/api/jobs?include_tag=Python&exclude_tag=Rejected")
    assert resp.status_code == 200
    ids = {j["id"] for j in resp.json()["items"]}
    assert ids == {job1}
    assert job3 not in ids


def test_include_and_exclude_same_tag_returns_empty():
    job1 = make_job("url1")
    tag_id = make_tag("Python")
    tag_job(job1, tag_id)

    resp = client.get("/api/jobs?include_tag=Python&exclude_tag=Python")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_multi_include_and_multi_exclude_combined():
    job1 = make_job("url1")   # Python → kept
    job2 = make_job("url2")   # React → kept
    job3 = make_job("url3")   # Python + Rejected → excluded
    job4 = make_job("url4")   # NotInterested → excluded
    job5 = make_job("url5")   # no tags → not in include results
    python_id = make_tag("Python")
    react_id = make_tag("React")
    rejected_id = make_tag("Rejected")
    not_interested_id = make_tag("NotInterested")
    tag_job(job1, python_id)
    tag_job(job2, react_id)
    tag_job(job3, python_id)
    tag_job(job3, rejected_id)
    tag_job(job4, not_interested_id)

    resp = client.get(
        "/api/jobs?include_tag=Python&include_tag=React"
        "&exclude_tag=Rejected&exclude_tag=NotInterested"
    )
    assert resp.status_code == 200
    ids = {j["id"] for j in resp.json()["items"]}
    assert ids == {job1, job2}


# ---------------------------------------------------------------------------
# include/exclude combined with is_repost
# ---------------------------------------------------------------------------

def test_include_tag_with_is_repost_originals():
    job1 = make_job("url1", is_repost=False)
    job2 = make_job("url2", is_repost=True)
    tag_id = make_tag("Python")
    tag_job(job1, tag_id)
    tag_job(job2, tag_id)

    resp = client.get("/api/jobs?include_tag=Python&is_repost=originals")
    assert resp.status_code == 200
    ids = {j["id"] for j in resp.json()["items"]}
    assert ids == {job1}


def test_all_filters_combined():
    job1 = make_job("url1", title="Senior Python Developer", is_repost=False)
    job2 = make_job("url2", title="Junior Python Developer", is_repost=False)
    job3 = make_job("url3", title="Senior Python Developer", is_repost=True)  # repost
    job4 = make_job("url4", title="Senior Python Developer", is_repost=False)  # Rejected
    python_id = make_tag("Python")
    rejected_id = make_tag("Rejected")
    for j in [job1, job2, job3, job4]:
        tag_job(j, python_id)
    tag_job(job4, rejected_id)

    resp = client.get(
        "/api/jobs?include_tag=Python&exclude_tag=Rejected&is_repost=originals&keyword=senior"
    )
    assert resp.status_code == 200
    ids = {j["id"] for j in resp.json()["items"]}
    assert ids == {job1}


# ---------------------------------------------------------------------------
# pagination total reflects filter
# ---------------------------------------------------------------------------

def test_filtered_total_matches_items_not_full_db():
    job1 = make_job("url1")
    job2 = make_job("url2")
    make_job("url3")   # untagged — should not appear
    tag_id = make_tag("Python")
    tag_job(job1, tag_id)
    tag_job(job2, tag_id)

    resp = client.get("/api/jobs?include_tag=Python&page_size=1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2      # filtered total, not 3
    assert len(data["items"]) == 1  # page_size honoured

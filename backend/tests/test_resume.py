import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/test_resume.db")

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from main import app
from database import engine
from models import ResumeVersion


@pytest.fixture(autouse=True)
def clean_db():
    from sqlmodel import SQLModel
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


client = TestClient(app)


def test_get_current_resume_empty():
    resp = client.get("/api/resume")
    assert resp.status_code == 404


def test_create_version():
    resp = client.post("/api/resume/versions", json={"label": "v1", "content": "<html>test</html>"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["label"] == "v1"
    assert data["content"] == "<html>test</html>"
    assert "id" in data
    assert "created_at" in data


def test_get_current_resume_returns_latest():
    client.post("/api/resume/versions", json={"label": "v1", "content": "first"})
    client.post("/api/resume/versions", json={"label": "v2", "content": "second"})
    resp = client.get("/api/resume")
    assert resp.status_code == 200
    assert resp.json()["label"] == "v2"
    assert resp.json()["content"] == "second"


def test_list_versions_excludes_content():
    client.post("/api/resume/versions", json={"label": "v1", "content": "first"})
    client.post("/api/resume/versions", json={"label": "v2", "content": "second"})
    resp = client.get("/api/resume/versions")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert "content" not in data[0]
    assert data[0]["label"] == "v2"


def test_get_version_by_id():
    v = client.post("/api/resume/versions", json={"label": "v1", "content": "my content"})
    vid = v.json()["id"]
    resp = client.get(f"/api/resume/versions/{vid}")
    assert resp.status_code == 200
    assert resp.json()["content"] == "my content"


def test_get_version_not_found():
    resp = client.get("/api/resume/versions/99999")
    assert resp.status_code == 404


def test_update_version_in_place():
    v = client.post("/api/resume/versions", json={"label": "v1", "content": "original"})
    vid = v.json()["id"]
    resp = client.put(f"/api/resume/versions/{vid}", json={"content": "edited"})
    assert resp.status_code == 200
    assert resp.json()["id"] == vid
    assert resp.json()["label"] == "v1"
    assert resp.json()["content"] == "edited"
    assert client.get(f"/api/resume/versions/{vid}").json()["content"] == "edited"
    assert len(client.get("/api/resume/versions").json()) == 1


def test_update_version_not_found():
    resp = client.put("/api/resume/versions/99999", json={"content": "x"})
    assert resp.status_code == 404


def test_delete_version():
    client.post("/api/resume/versions", json={"label": "v1", "content": "first"})
    v2 = client.post("/api/resume/versions", json={"label": "v2", "content": "second"})
    v2_id = v2.json()["id"]
    resp = client.delete(f"/api/resume/versions/{v2_id}")
    assert resp.status_code == 204
    assert len(client.get("/api/resume/versions").json()) == 1


def test_delete_last_version_returns_400():
    v = client.post("/api/resume/versions", json={"label": "only", "content": "content"})
    resp = client.delete(f"/api/resume/versions/{v.json()['id']}")
    assert resp.status_code == 400

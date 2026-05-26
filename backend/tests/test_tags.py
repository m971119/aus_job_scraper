import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from main import app
from database import engine
from models import Tag

client = TestClient(app)

DEFAULT_TAGS = ["Interested", "Laravel", "Python", "AI"]


@pytest.fixture(autouse=True)
def clean_db():
    from sqlmodel import SQLModel
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


def seed_defaults():
    with Session(engine) as s:
        for name in DEFAULT_TAGS:
            s.add(Tag(name=name))
        s.commit()


def test_list_tags_empty():
    resp = client.get("/api/tags")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_tags_returns_defaults():
    seed_defaults()
    resp = client.get("/api/tags")
    assert resp.status_code == 200
    names = {t["name"] for t in resp.json()}
    assert names == set(DEFAULT_TAGS)


def test_create_tag():
    resp = client.post("/api/tags", json={"name": "Django"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Django"
    assert "id" in data


def test_create_tag_duplicate_rejected():
    client.post("/api/tags", json={"name": "Django"})
    resp = client.post("/api/tags", json={"name": "Django"})
    assert resp.status_code == 409


def test_create_tag_case_insensitive_duplicate():
    client.post("/api/tags", json={"name": "Python"})
    resp = client.post("/api/tags", json={"name": "python"})
    assert resp.status_code == 409


def test_create_tag_empty_name_rejected():
    resp = client.post("/api/tags", json={"name": ""})
    assert resp.status_code == 422

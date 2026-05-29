from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_sponsors_returns_200():
    resp = client.get("/api/sponsors")
    assert resp.status_code == 200


def test_sponsors_returns_list_of_strings():
    resp = client.get("/api/sponsors")
    data = resp.json()
    assert "sponsors" in data
    assert isinstance(data["sponsors"], list)
    assert all(isinstance(s, str) for s in data["sponsors"])


def test_sponsors_list_is_nonempty():
    resp = client.get("/api/sponsors")
    assert len(resp.json()["sponsors"]) > 0

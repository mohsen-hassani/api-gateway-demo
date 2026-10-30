import pytest
from fastapi.testclient import TestClient

from app.main import create
from common.settings import Settings
from common.testing import CommonBehaviourTests, DebugAndFaultTests


@pytest.fixture
def make_client():
    return lambda **kw: TestClient(create(Settings(service_name="newsletter-service", **kw)))


@pytest.fixture
def client(make_client):
    return make_client()


def test_unsubscribe_by_token(client):
    r = client.get("/unsubscribe?token=abc")
    assert r.status_code == 200
    assert r.json()["status"] == "unsubscribed" and r.json()["message"]


@pytest.mark.parametrize("url", ["/unsubscribe", "/unsubscribe?token=", "/unsubscribe?token=%20"])
def test_unsubscribe_requires_token(client, url):
    r = client.get(url)
    assert r.status_code == 422 and r.json()["error"] == "invalid_input"


def test_unsubscribe_by_email_is_idempotent(client):
    first = client.post("/unsubscribe", json={"email": "Bob@Example.com "})
    second = client.post("/unsubscribe", json={"email": "bob@example.com"})
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert client.app.state.unsubscribed_emails == {"bob@example.com"}


@pytest.mark.parametrize("body", [{"email": "not-an-email"}, {"email": ""}, {}, {"email": 5}])
def test_unsubscribe_rejects_bad_email(client, body):
    r = client.post("/unsubscribe", json=body)
    assert r.status_code == 422 and r.json()["error"] == "invalid_input"


def test_unsubscribe_rejects_non_json(client):
    r = client.post("/unsubscribe", content=b"nope", headers={"content-type": "application/json"})
    assert r.status_code == 422 and r.json()["error"] == "invalid_input"


class TestCommonBehaviour(CommonBehaviourTests, DebugAndFaultTests):
    service_name = "newsletter-service"
    sample_path = "/unsubscribe?token=x"

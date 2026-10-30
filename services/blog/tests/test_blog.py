import pytest
from fastapi.testclient import TestClient

from app.main import create
from common.settings import Settings
from common.testing import CommonBehaviourTests, DebugAndFaultTests, test_unhandled_exception_keeps_error_shape_and_headers  # noqa: F401


@pytest.fixture
def make_client():
    return lambda **kw: TestClient(create(Settings(service_name="blog-service", **kw)))


@pytest.fixture
def client(make_client):
    return make_client()


def test_list_posts(client):
    posts = client.get("/posts").json()["posts"]
    assert [p["id"] for p in posts] == [1, 2, 3, 4, 5]
    assert set(posts[0]) >= {"id", "title", "author", "published_at", "summary"}


def test_get_post_includes_body(client):
    post = client.get("/posts/3").json()
    assert post["id"] == 3 and post["body"]


def test_unknown_post(client):
    r = client.get("/posts/99")
    assert r.status_code == 404
    assert r.json() == {"error": "post_not_found", "message": "No post with id 99", "path": "/posts/99"}


def test_non_integer_id(client):
    r = client.get("/posts/abc")
    assert r.status_code == 422 and r.json()["error"] == "invalid_input"


class TestCommonBehaviour(CommonBehaviourTests, DebugAndFaultTests):
    service_name = "blog-service"
    sample_path = "/posts"

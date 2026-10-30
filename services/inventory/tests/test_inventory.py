import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import create
from common import upstream
from common.settings import Settings
from common.testing import CommonBehaviourTests, DebugAndFaultTests


def pricing(handler):
    upstream.TRANSPORT = httpx.MockTransport(handler)


@pytest.fixture(autouse=True)
def reset_transport():
    yield
    upstream.TRANSPORT = None


def ok_pricing(request: httpx.Request):
    sku = request.url.path.rsplit("/", 1)[1]
    return httpx.Response(200, json={"sku": sku, "amount": 19.99, "currency": "EUR"})


@pytest.fixture
def make_client():
    def make(**kw):
        pricing(ok_pricing)
        return TestClient(create(Settings(service_name="inventory-service", **kw)))

    return make


@pytest.fixture
def client(make_client):
    return make_client()


def test_stock_includes_price(client):
    r = client.get("/stock/SKU-002")
    assert r.status_code == 200
    assert r.json() == {
        "sku": "SKU-002",
        "in_stock": 42,
        "price": {"amount": 19.99, "currency": "EUR"},
    }


def test_stock_is_fixed(client):
    assert client.get("/stock/SKU-002").json() == client.get("/stock/SKU-002").json()


def test_unknown_sku_does_not_call_pricing(client):
    calls = []
    pricing(lambda request: calls.append(request) or ok_pricing(request))
    r = client.get("/stock/SKU-999")
    assert r.status_code == 404 and r.json()["error"] == "unknown_sku"
    assert calls == []


def test_request_id_is_forwarded_to_pricing(client):
    seen = []
    pricing(lambda request: seen.append(request.headers["x-request-id"]) or ok_pricing(request))
    client.get("/stock/SKU-001", headers={"x-request-id": "chain-1"})
    assert seen == ["chain-1"]


def test_faults_are_not_forwarded_to_pricing(client):
    seen = []
    pricing(lambda request: seen.append(str(request.url)) or ok_pricing(request))
    assert client.get("/stock/SKU-001?delay_ms=1").status_code == 200
    assert "delay_ms" not in seen[0]


def test_pricing_down_gives_502(client):
    def refuse(request):
        raise httpx.ConnectError("refused")

    pricing(refuse)
    r = client.get("/stock/SKU-001")
    assert r.status_code == 502 and r.json()["error"] == "upstream_unavailable"


def test_pricing_timeout_gives_502(client):
    def slow(request):
        raise httpx.ReadTimeout("slow")

    pricing(slow)
    assert client.get("/stock/SKU-001").status_code == 502


def test_pricing_error_status_gives_502(client):
    pricing(lambda request: httpx.Response(503, json={}))
    assert client.get("/stock/SKU-001").status_code == 502


class TestCommonBehaviour(CommonBehaviourTests, DebugAndFaultTests):
    service_name = "inventory-service"
    sample_path = "/stock/SKU-001"

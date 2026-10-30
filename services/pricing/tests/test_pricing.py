import pytest
from fastapi.testclient import TestClient

from app.main import create
from common.settings import Settings
from common.testing import CommonBehaviourTests, DebugAndFaultTests


@pytest.fixture
def make_client():
    return lambda **kw: TestClient(create(Settings(service_name="pricing-service", **kw)))


@pytest.fixture
def client(make_client):
    return make_client()


def test_price(client):
    assert client.get("/price/SKU-002").json() == {"sku": "SKU-002", "amount": 19.99, "currency": "EUR"}


def test_all_catalog_skus_have_prices(client):
    for n in range(1, 6):
        assert client.get(f"/price/SKU-00{n}").status_code == 200


def test_unknown_sku(client):
    r = client.get("/price/SKU-999")
    assert r.status_code == 404 and r.json()["error"] == "unknown_sku"


class TestCommonBehaviour(CommonBehaviourTests, DebugAndFaultTests):
    service_name = "pricing-service"
    sample_path = "/price/SKU-001"

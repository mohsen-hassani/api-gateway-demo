import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import create
from common import upstream
from common.settings import Settings
from common.testing import CommonBehaviourTests, DebugAndFaultTests

ALICE = {"x-user-id": "user-alice", "x-user-email": "alice@example.com"}


def fake_inventory(request: httpx.Request):
    sku = request.url.path.rsplit("/", 1)[1]
    if not sku.startswith("SKU-00") or sku > "SKU-005":
        return httpx.Response(404, json={"error": "unknown_sku"})
    return httpx.Response(
        200, json={"sku": sku, "in_stock": 42, "price": {"amount": 19.99, "currency": "EUR"}}
    )


@pytest.fixture(autouse=True)
def mock_inventory():
    upstream.TRANSPORT = httpx.MockTransport(fake_inventory)
    yield
    upstream.TRANSPORT = None


@pytest.fixture
def make_client():
    def make(version="v1", **kw):
        return TestClient(create(Settings(service_name="orders-service", version=version, **kw)))

    return make


@pytest.fixture
def client(make_client):
    return make_client()


# --- identity -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "headers",
    [{}, {"x-user-id": "u1"}, {"x-user-email": "a@b.co"}, {"x-user-id": "", "x-user-email": "a@b.co"}],
)
@pytest.mark.parametrize("method,path", [("get", "/orders"), ("get", "/orders/ord-1"), ("post", "/orders")])
def test_missing_identity_is_401(client, headers, method, path):
    r = getattr(client, method)(path, headers=headers)
    assert r.status_code == 401 and r.json()["error"] == "missing_identity"


def test_identity_check_comes_before_body_validation(client):
    r = client.post("/orders", content=b"not json", headers={"content-type": "application/json"})
    assert r.status_code == 401


# --- listing and shapes ---------------------------------------------------------------------


def test_list_orders_v1_shape(client):
    body = client.get("/orders", headers=ALICE).json()
    assert body["user_id"] == "user-alice"
    assert body["user_email"] == "alice@example.com"
    assert body["version"] == "v1"
    assert "recommendations" not in body
    assert len(body["orders"]) == 2
    order = body["orders"][0]
    assert set(order) == {"id", "sku", "quantity", "created_at", "stock"}
    assert order["stock"]["price"] == {"amount": 19.99, "currency": "EUR"}
    assert order["id"].startswith("ord-") and order["created_at"].endswith("Z")


def test_list_orders_v2_adds_recommendations(make_client):
    body = make_client("v2").get("/orders", headers=ALICE).json()
    assert body["version"] == "v2"
    recs = body["recommendations"]
    assert 0 < len(recs) <= 2
    ordered = {o["sku"] for o in body["orders"]}
    assert not ordered & set(recs)


def test_v2_recommendations_also_on_single_order_and_create(make_client):
    client = make_client("v2")
    first = client.get("/orders", headers=ALICE).json()["orders"][0]
    assert "recommendations" in client.get(f"/orders/{first['id']}", headers=ALICE).json()
    created = client.post("/orders", json={"sku": "SKU-001", "quantity": 1}, headers=ALICE)
    assert "recommendations" in created.json()


# --- determinism ----------------------------------------------------------------------------


def test_seeding_is_deterministic_across_instances_and_versions(make_client):
    a = make_client("v1").get("/orders", headers=ALICE).json()["orders"]
    b = make_client("v1").get("/orders", headers=ALICE).json()["orders"]
    c = make_client("v2").get("/orders", headers=ALICE).json()["orders"]
    assert a == b == c


def test_different_users_get_different_orders(client):
    other = {"x-user-id": "user-bob", "x-user-email": "bob@example.com"}
    a = client.get("/orders", headers=ALICE).json()["orders"]
    b = client.get("/orders", headers=other).json()["orders"]
    assert [o["id"] for o in a] != [o["id"] for o in b]


def test_seeded_order_is_fetchable_on_a_fresh_instance(make_client):
    order_id = make_client().get("/orders", headers=ALICE).json()["orders"][1]["id"]
    r = make_client("v2").get(f"/orders/{order_id}", headers=ALICE)
    assert r.status_code == 200
    body = r.json()
    assert body["order"]["id"] == order_id and "orders" not in body


# --- single order ---------------------------------------------------------------------------


def test_unknown_order_is_404(client):
    r = client.get("/orders/ord-nope", headers=ALICE)
    assert r.status_code == 404 and r.json()["error"] == "order_not_found"


def test_other_users_order_is_404(client):
    bob = {"x-user-id": "user-bob", "x-user-email": "bob@example.com"}
    bobs_id = client.get("/orders", headers=bob).json()["orders"][0]["id"]
    assert client.get(f"/orders/{bobs_id}", headers=ALICE).status_code == 404


# --- creating -------------------------------------------------------------------------------


def test_create_order(client):
    r = client.post("/orders", json={"sku": "SKU-003", "quantity": 4}, headers=ALICE)
    assert r.status_code == 201
    order = r.json()["order"]
    assert order["sku"] == "SKU-003" and order["quantity"] == 4
    assert order["stock"]["sku"] == "SKU-003"
    listed = client.get("/orders", headers=ALICE).json()["orders"]
    assert [o["id"] for o in listed][-1] == order["id"] and len(listed) == 3
    assert client.get(f"/orders/{order['id']}", headers=ALICE).status_code == 200


def test_created_order_exists_only_on_that_instance(make_client):
    one, two = make_client(), make_client()
    order_id = one.post("/orders", json={"sku": "SKU-001", "quantity": 1}, headers=ALICE).json()["order"]["id"]
    assert two.get(f"/orders/{order_id}", headers=ALICE).status_code == 404


@pytest.mark.parametrize("quantity", [0, 11, -1, 1.5, "2", None, True])
def test_create_validates_quantity(client, quantity):
    r = client.post("/orders", json={"sku": "SKU-001", "quantity": quantity}, headers=ALICE)
    assert r.status_code == 422 and r.json()["error"] == "invalid_input"


@pytest.mark.parametrize("body", [{}, {"quantity": 1}, [], "text"])
def test_create_validates_body(client, body):
    r = client.post("/orders", json=body, headers=ALICE)
    assert r.status_code == 422 and r.json()["error"] == "invalid_input"


def test_create_rejects_non_json(client):
    r = client.post("/orders", content=b"{", headers={**ALICE, "content-type": "application/json"})
    assert r.status_code == 422 and r.json()["error"] == "invalid_input"


def test_create_with_unknown_sku(client):
    r = client.post("/orders", json={"sku": "SKU-999", "quantity": 1}, headers=ALICE)
    assert r.status_code == 422 and r.json()["error"] == "unknown_sku"
    assert len(client.get("/orders", headers=ALICE).json()["orders"]) == 2


# --- downstream -----------------------------------------------------------------------------


def test_inventory_unreachable_is_502(client):
    def refuse(request):
        raise httpx.ConnectError("refused")

    upstream.TRANSPORT = httpx.MockTransport(refuse)
    for call in (
        lambda: client.get("/orders", headers=ALICE),
        lambda: client.post("/orders", json={"sku": "SKU-001", "quantity": 1}, headers=ALICE),
    ):
        r = call()
        assert r.status_code == 502 and r.json()["error"] == "upstream_unavailable"


def test_inventory_timeout_and_5xx_are_502(client):
    def slow(request):
        raise httpx.ReadTimeout("slow")

    upstream.TRANSPORT = httpx.MockTransport(slow)
    assert client.get("/orders", headers=ALICE).status_code == 502
    upstream.TRANSPORT = httpx.MockTransport(lambda r: httpx.Response(502, json={}))
    assert client.get("/orders", headers=ALICE).status_code == 502


def test_request_id_is_sent_to_inventory(client):
    seen = []

    def spy(request):
        seen.append(request.headers["x-request-id"])
        return fake_inventory(request)

    upstream.TRANSPORT = httpx.MockTransport(spy)
    client.get("/orders", headers={**ALICE, "x-request-id": "chain-7"})
    assert seen == ["chain-7", "chain-7"]


def test_fault_params_are_not_forwarded(client):
    seen = []
    upstream.TRANSPORT = httpx.MockTransport(lambda r: seen.append(str(r.url)) or fake_inventory(r))
    assert client.get("/orders?delay_ms=1", headers=ALICE).status_code == 200
    assert seen and all("?" not in url for url in seen)


class TestCommonBehaviour(CommonBehaviourTests, DebugAndFaultTests):
    service_name = "orders-service"
    sample_path = "/debug/request"

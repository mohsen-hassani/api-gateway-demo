import asyncio
import hashlib
import os
from datetime import datetime, timedelta, timezone

from fastapi import Request
from pydantic import BaseModel, Field, StrictInt, ValidationError

from common import upstream
from common.app import create_app
from common.errors import ApiError
from common.seed import SKUS
from common.settings import Settings

SEED_EPOCH = datetime(2026, 1, 1, tzinfo=timezone.utc)


class OrderIn(BaseModel):
    sku: str
    quantity: StrictInt = Field(ge=1, le=10)


def seed_orders(user_id: str) -> list[dict]:
    """Two orders derived only from the user id, so every instance agrees."""
    digest = hashlib.sha256(user_id.encode()).digest()
    prefix = digest[:4].hex()
    orders = []
    for n in (1, 2):
        chunk = digest[4 * n : 4 * n + 4]
        created = SEED_EPOCH + timedelta(hours=int.from_bytes(chunk[:2], "big") % 2000)
        orders.append(
            {
                "id": f"ord-{prefix}-{n}",
                "sku": SKUS[chunk[2] % len(SKUS)],
                "quantity": 1 + chunk[3] % 10,
                "created_at": created.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        )
    return orders


def create(settings: Settings | None = None):
    settings = settings or Settings.from_env("orders-service")
    app = create_app(settings)
    store: dict[str, list[dict]] = {}
    app.state.orders = store

    def inventory_url() -> str:
        return os.environ.get("INVENTORY_URL", "http://inventory-service:8004")

    def timeout() -> float:
        return float(os.environ.get("UPSTREAM_TIMEOUT_SECONDS", "2"))

    def identity(request: Request) -> tuple[str, str]:
        user_id = request.headers.get("x-user-id", "")
        user_email = request.headers.get("x-user-email", "")
        if not user_id.strip() or not user_email.strip():
            raise ApiError(401, "missing_identity", "x-user-id and x-user-email headers are required")
        return user_id, user_email

    def orders_for(user_id: str) -> list[dict]:
        if user_id not in store:
            store[user_id] = seed_orders(user_id)
        return store[user_id]

    async def stock_for(sku: str) -> dict:
        response = await upstream.get(inventory_url(), f"/stock/{sku}", timeout=timeout())
        if response.status_code == 404:
            raise ApiError(422, "unknown_sku", f"Unknown SKU {sku}")
        if response.status_code != 200:
            raise ApiError(502, "upstream_unavailable", f"inventory-service answered {response.status_code}")
        return response.json()

    async def with_stock(orders: list[dict]) -> list[dict]:
        stocks = await asyncio.gather(*(stock_for(o["sku"]) for o in orders))
        return [{**order, "stock": stock} for order, stock in zip(orders, stocks)]

    def envelope(user_id: str, user_email: str, **payload) -> dict:
        body = {"user_id": user_id, "user_email": user_email, "version": settings.version, **payload}
        if settings.version == "v2":
            ordered = {o["sku"] for o in orders_for(user_id)}
            body["recommendations"] = [sku for sku in SKUS if sku not in ordered][:2]
        return body

    @app.get("/orders")
    async def list_orders(request: Request):
        user_id, user_email = identity(request)
        orders = await with_stock(orders_for(user_id))
        return envelope(user_id, user_email, orders=orders)

    @app.get("/orders/{order_id}")
    async def get_order(order_id: str, request: Request):
        user_id, user_email = identity(request)
        for order in orders_for(user_id):
            if order["id"] == order_id:
                (with_stock_order,) = await with_stock([order])
                return envelope(user_id, user_email, order=with_stock_order)
        raise ApiError(404, "order_not_found", f"No order {order_id}")

    @app.post("/orders", status_code=201)
    async def create_order(request: Request):
        user_id, user_email = identity(request)
        try:
            body = OrderIn.model_validate(await request.json())
        except (ValueError, ValidationError) as exc:
            raise ApiError(422, "invalid_input", _describe(exc)) from exc
        stock = await stock_for(body.sku)  # also rejects unknown SKUs
        orders = orders_for(user_id)
        prefix = orders[0]["id"].rsplit("-", 1)[0]
        order = {
            "id": f"{prefix}-{len(orders) + 1}",
            "sku": body.sku,
            "quantity": body.quantity,
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        orders.append(order)
        return envelope(user_id, user_email, order={**order, "stock": stock})

    return app


def _describe(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        first = exc.errors()[0]
        return f"{'.'.join(str(p) for p in first['loc'])}: {first['msg']}"
    return "Request body must be a JSON object with sku and quantity"


app = create()

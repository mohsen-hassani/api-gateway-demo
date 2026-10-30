import os

from common import upstream
from common.app import create_app
from common.errors import ApiError
from common.seed import CATALOG
from common.settings import Settings


def create(settings: Settings | None = None):
    settings = settings or Settings.from_env("inventory-service")
    app = create_app(settings)

    @app.get("/stock/{sku}")
    async def get_stock(sku: str):
        item = CATALOG.get(sku)
        if item is None:
            raise ApiError(404, "unknown_sku", f"Unknown SKU {sku}")
        response = await upstream.get(
            os.environ.get("PRICING_URL", "http://pricing-service:8005"),
            f"/price/{sku}",
            timeout=float(os.environ.get("UPSTREAM_TIMEOUT_SECONDS", "2")),
        )
        if response.status_code != 200:
            raise ApiError(502, "upstream_unavailable", f"pricing-service answered {response.status_code}")
        price = response.json()
        return {
            "sku": sku,
            "in_stock": item["stock"],
            "price": {"amount": price["amount"], "currency": price["currency"]},
        }

    return app


app = create()

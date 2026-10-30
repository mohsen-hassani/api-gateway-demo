from common.app import create_app
from common.errors import ApiError
from common.seed import CATALOG, CURRENCY
from common.settings import Settings


def create(settings: Settings | None = None):
    settings = settings or Settings.from_env("pricing-service")
    app = create_app(settings)

    @app.get("/price/{sku}")
    async def get_price(sku: str):
        item = CATALOG.get(sku)
        if item is None:
            raise ApiError(404, "unknown_sku", f"Unknown SKU {sku}")
        return {"sku": sku, "amount": item["price"], "currency": CURRENCY}

    return app


app = create()

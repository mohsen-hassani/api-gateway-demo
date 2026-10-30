"""Application factory: everything the services have in common (spec section 7)."""
import asyncio
import random
import time
import uuid
from urllib.parse import parse_qs

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.datastructures import MutableHeaders
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import jsonlog
from .errors import ApiError
from .settings import Settings

PROBE_PATHS = {"/healthz", "/readyz", "/metrics"}
MAX_DELAY_MS = 10_000
ALL_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]


def raw_path(scope) -> str:
    """The path exactly as the service received it (no query string)."""
    raw = scope.get("raw_path")
    return raw.decode("latin-1").split("?", 1)[0] if raw else scope["path"]


def error_response(scope, status: int, code: str, message: str, *, include_path: bool, headers=None):
    body = {"error": code, "message": message}
    if include_path:
        body["path"] = raw_path(scope)
    return JSONResponse(body, status_code=status, headers=headers)


class CommonMiddleware:
    """Request id, response headers, fault injection and the JSON request log."""

    def __init__(self, app, *, settings: Settings, faults: bool, error_path: bool):
        self.app = app
        self.settings = settings
        self.faults = faults
        self.error_path = error_path

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        s = self.settings
        incoming = {k.decode("latin-1"): v.decode("latin-1") for k, v in scope["headers"]}
        request_id = incoming.get("x-request-id") or str(uuid.uuid4())
        rid_token = jsonlog.request_id_var.set(request_id)
        ctx_token = jsonlog.context_var.set(
            {"service": s.service_name, "version": s.version, "instance": s.instance}
        )
        status = 500
        started = time.perf_counter()

        async def send_with_headers(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                headers = MutableHeaders(scope=message)
                headers["x-service-name"] = s.service_name
                headers["x-service-version"] = s.version
                headers["x-instance-id"] = s.instance
                headers["x-request-id"] = request_id
            await send(message)

        try:
            fault = await self._inject_fault(scope) if self.faults else None
            if fault is not None:
                await fault(scope, receive, send_with_headers)
            else:
                await self.app(scope, receive, send_with_headers)
        except Exception as exc:  # noqa: BLE001 - last resort, keep the error shape
            jsonlog.log("error", event="unhandled_exception", error=repr(exc))
            response = error_response(
                scope, 500, "internal_error", "Internal server error", include_path=self.error_path
            )
            await response(scope, receive, send_with_headers)
        finally:
            jsonlog.log(
                "error" if status >= 500 else "info",
                method=scope["method"],
                path=raw_path(scope),
                status=status,
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
            )
            jsonlog.request_id_var.reset(rid_token)
            jsonlog.context_var.reset(ctx_token)

    async def _inject_fault(self, scope):
        """Apply ?delay_ms, ?fail and FAIL_RATE. Returns a response to send, or None."""
        if scope["path"] in PROBE_PATHS:
            return None
        query = parse_qs(scope["query_string"].decode("latin-1"))

        def invalid(message):
            return error_response(scope, 422, "invalid_input", message, include_path=self.error_path)

        delay_ms = fail = None
        if "delay_ms" in query:
            try:
                delay_ms = int(query["delay_ms"][0])
            except ValueError:
                return invalid("delay_ms must be an integer")
            if delay_ms < 0:
                return invalid("delay_ms must not be negative")
        if "fail" in query:
            try:
                fail = int(query["fail"][0])
            except ValueError:
                return invalid("fail must be an integer from 400 to 599")
            if not 400 <= fail <= 599:
                return invalid("fail must be an integer from 400 to 599")

        if delay_ms:
            await asyncio.sleep(min(delay_ms, MAX_DELAY_MS) / 1000)
        if fail is not None:
            return error_response(
                scope, fail, "injected_failure", f"Injected failure with status {fail}",
                include_path=self.error_path,
            )
        if self.settings.fail_rate > 0 and random.random() < self.settings.fail_rate:
            return error_response(
                scope, 503, "injected_failure", "Injected failure (FAIL_RATE)",
                include_path=self.error_path,
            )
        return None


def create_app(
    settings: Settings,
    *,
    debug_endpoint: bool = True,
    faults: bool = True,
    metrics: bool = True,
    error_path: bool = True,
    docs: bool = True,
) -> FastAPI:
    app = FastAPI(
        title=settings.service_name,
        docs_url="/docs" if docs else None,
        redoc_url="/redoc" if docs else None,
        openapi_url="/openapi.json" if docs else None,
        redirect_slashes=False,
    )
    app.state.settings = settings

    def error(request: Request, status: int, code: str, message: str, headers=None):
        return error_response(request.scope, status, code, message, include_path=error_path, headers=headers)

    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError):
        return error(request, exc.status, exc.code, exc.message)

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException):
        codes = {404: "not_found", 405: "method_not_allowed"}
        defaults = {404: "Not found", 405: "Method not allowed"}
        message = exc.detail if isinstance(exc.detail, str) else defaults.get(exc.status_code, "Error")
        if exc.status_code in defaults:
            message = defaults[exc.status_code]
        code = codes.get(exc.status_code, "http_error")
        return error(request, exc.status_code, code, message, headers=getattr(exc, "headers", None))

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        first = exc.errors()[0] if exc.errors() else {}
        where = ".".join(str(p) for p in first.get("loc", ()) if p != "body")
        message = f"{where}: {first['msg']}" if where else first.get("msg", "Invalid input")
        return error(request, 422, "invalid_input", message)

    @app.get("/healthz", include_in_schema=False)
    async def healthz():
        return {"status": "ok"}

    @app.get("/readyz", include_in_schema=False)
    async def readyz():
        return {"status": "ready"}

    if debug_endpoint:

        @app.get("/debug/request", include_in_schema=False)
        @app.api_route("/debug/request/{path:path}", methods=ALL_METHODS, include_in_schema=False)
        async def debug_request(request: Request):
            headers: dict = {}
            for key, value in request.scope["headers"]:
                name, text = key.decode("latin-1").lower(), value.decode("latin-1")
                if name not in headers:
                    headers[name] = text
                elif isinstance(headers[name], list):
                    headers[name].append(text)
                else:
                    headers[name] = [headers[name], text]
            client = request.client
            return {
                "service": settings.service_name,
                "version": settings.version,
                "instance": settings.instance,
                "method": request.method,
                "path": raw_path(request.scope),
                "query": request.scope["query_string"].decode("latin-1"),
                "headers": headers,
                "client": f"{client.host}:{client.port}" if client else None,
            }

    if metrics:
        from prometheus_fastapi_instrumentator import Instrumentator

        Instrumentator().instrument(app).expose(app, include_in_schema=False)

    app.add_middleware(
        CommonMiddleware, settings=settings, faults=faults, error_path=error_path
    )
    return app

"""Calls to downstream services. Failures all become 502 upstream_unavailable."""
import httpx

from . import jsonlog as jlog
from .errors import ApiError

# Tests replace this with an httpx.MockTransport.
TRANSPORT: httpx.AsyncBaseTransport | None = None


async def get(base_url: str, path: str, *, timeout: float) -> httpx.Response:
    """GET base_url+path, forwarding the request id. Raises ApiError(502) if the
    downstream is unreachable, too slow, or answers with a 5xx status."""
    url = base_url.rstrip("/") + path
    headers = {"x-request-id": jlog.request_id_var.get()}
    try:
        async with httpx.AsyncClient(transport=TRANSPORT, timeout=timeout) as client:
            response = await client.get(url, headers=headers)
    except httpx.HTTPError as exc:
        jlog.log("warning", event="upstream_failure", upstream=url, error=type(exc).__name__)
        raise ApiError(502, "upstream_unavailable", f"Could not reach {base_url}") from exc
    if response.status_code >= 500:
        jlog.log("warning", event="upstream_failure", upstream=url, status=response.status_code)
        raise ApiError(502, "upstream_unavailable", f"{base_url} answered {response.status_code}")
    return response

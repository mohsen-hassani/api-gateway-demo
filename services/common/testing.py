"""Shared tests for the behaviour every Python service has in common (spec section 7).

A service's tests subclass ``CommonBehaviourTests`` as ``TestCommonBehaviour`` and provide
a ``client`` fixture, the expected ``service_name``, and a ``sample_path`` that returns 200
(used to check faults on a real endpoint).
"""
import re
import uuid

from fastapi.testclient import TestClient

from .app import create_app
from .settings import Settings


class CommonBehaviourTests:
    service_name: str
    sample_path: str = "/healthz"

    # --- probes ---------------------------------------------------------------------------

    def test_probes(self, client):
        assert client.get("/healthz").status_code == 200
        assert client.get("/readyz").status_code == 200

    def test_probes_ignore_fault_injection(self, client):
        assert client.get("/healthz?fail=503").status_code == 200
        assert client.get("/readyz?fail=500&delay_ms=1").status_code == 200

    # --- headers --------------------------------------------------------------------------

    def test_response_headers_on_success_and_error(self, client):
        for path in (self.sample_path, "/does-not-exist"):
            r = client.get(path)
            assert r.headers["x-service-name"] == self.service_name
            assert r.headers["x-service-version"]
            assert r.headers["x-instance-id"]
            assert r.headers["x-request-id"]

    # --- errors ---------------------------------------------------------------------------

    def test_unknown_path_uses_error_shape(self, client):
        r = client.get("/does-not-exist")
        assert r.status_code == 404
        body = r.json()
        assert body["error"] == "not_found"
        assert body["message"]
        assert body.get("path", "/does-not-exist") == "/does-not-exist"

    def test_wrong_method_uses_error_shape(self, client):
        r = client.delete("/healthz")
        assert r.status_code == 405
        assert r.json()["error"] == "method_not_allowed"

    # --- request ids ----------------------------------------------------------------------

    def test_request_id_is_echoed(self, client):
        r = client.get(self.sample_path, headers={"x-request-id": "abc-123"})
        assert r.headers["x-request-id"] == "abc-123"

    def test_request_id_is_generated(self, client):
        r = client.get(self.sample_path)
        assert str(uuid.UUID(r.headers["x-request-id"]))

    # --- logging --------------------------------------------------------------------------

    def test_request_is_logged_as_json(self, client, capsys):
        import json

        client.get(self.sample_path, headers={"x-request-id": "log-me"})
        lines = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.startswith("{")]
        entry = next(line for line in lines if line.get("request_id") == "log-me")
        for field in ("timestamp", "level", "service", "version", "instance", "method",
                      "path", "status", "duration_ms", "request_id"):
            assert field in entry
        assert entry["service"] == self.service_name
        assert entry["path"] == self.sample_path.split("?")[0]


class DebugAndFaultTests:
    """For services that have /debug/request and fault injection (all but auth)."""

    sample_path: str

    def with_query(self, extra: str) -> str:
        return self.sample_path + ("&" if "?" in self.sample_path else "?") + extra

    def test_debug_request_echo(self, client):
        r = client.get("/debug/request/anything/else?a=1&b=2", headers={"x-gateway": "envoy"})
        assert r.status_code == 200
        body = r.json()
        assert body["method"] == "GET"
        assert body["path"] == "/debug/request/anything/else"
        assert body["query"] == "a=1&b=2"
        assert body["headers"]["x-gateway"] == "envoy"
        assert body["client"]

    def test_debug_request_any_method_and_plain_path(self, client):
        assert client.get("/debug/request").json()["path"] == "/debug/request"
        r = client.post("/debug/request/x", json={})
        assert r.status_code == 200 and r.json()["method"] == "POST"

    def test_debug_request_lists_repeated_headers(self, client):
        r = client.get("/debug/request", headers=[("x-multi", "one"), ("x-multi", "two")])
        assert r.json()["headers"]["x-multi"] == ["one", "two"]

    def test_fail_parameter(self, client):
        r = client.get(self.with_query("fail=503"))
        assert r.status_code == 503
        assert r.json()["error"] == "injected_failure"
        assert client.get(self.with_query("fail=404")).status_code == 404

    def test_fail_parameter_rejects_non_error_statuses(self, client):
        for value in ("200", "399", "600", "abc"):
            r = client.get(self.with_query(f"fail={value}"))
            assert r.status_code == 422 and r.json()["error"] == "invalid_input"

    def test_delay_parameter(self, client):
        import time

        started = time.perf_counter()
        assert client.get(self.with_query("delay_ms=120")).status_code == 200
        assert time.perf_counter() - started >= 0.12
        assert client.get(self.with_query("delay_ms=-1")).status_code == 422

    def test_fail_rate(self, make_client):
        always = make_client(fail_rate=1.0)
        r = always.get(self.sample_path)
        assert r.status_code == 503 and r.json()["error"] == "injected_failure"
        assert always.get("/healthz").status_code == 200
        never = make_client(fail_rate=0.0)
        assert never.get(self.sample_path).status_code == 200

    def test_metrics_exempt_from_faults(self, client):
        assert client.get("/metrics?fail=503").status_code == 200


def test_unhandled_exception_keeps_error_shape_and_headers():
    app = create_app(Settings(service_name="boom-service"), metrics=False)

    @app.get("/boom")
    async def boom():
        raise RuntimeError("kaboom")

    r = TestClient(app, raise_server_exceptions=False).get("/boom")
    assert r.status_code == 500
    assert r.json()["error"] == "internal_error"
    assert r.headers["x-service-name"] == "boom-service"
    assert re.match(r"^[0-9a-f-]{36}$", r.headers["x-request-id"])

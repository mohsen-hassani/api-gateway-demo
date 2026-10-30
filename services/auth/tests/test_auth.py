import base64
import json

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app import keys
from app.main import create
from common.settings import Settings
from common.testing import CommonBehaviourTests

CREDS = {"email": "alice@example.com", "password": "correct horse"}


@pytest.fixture
def key_file(tmp_path):
    private = keys.generate_private_key()
    path = tmp_path / "jwt-private.pem"
    path.write_bytes(keys.private_key_pem(private))
    return path, private


@pytest.fixture
def client(key_file, monkeypatch):
    monkeypatch.setenv("JWT_PRIVATE_KEY_PATH", str(key_file[0]))
    monkeypatch.setenv("BCRYPT_ROUNDS", "4")
    return TestClient(create(Settings(service_name="auth-service")))


def register(client, **overrides):
    return client.post("/register", json={**CREDS, **overrides})


def login(client, **overrides):
    return client.post("/login", json={**CREDS, **overrides})


# --- register -------------------------------------------------------------------------------


def test_register(client):
    r = register(client)
    assert r.status_code == 201
    assert set(r.json()) == {"id", "email"} and r.json()["email"] == "alice@example.com"


def test_duplicate_register_is_409(client):
    register(client)
    r = register(client)
    assert r.status_code == 409
    assert r.json() == {"error": "email_taken", "message": r.json()["message"]}


def test_email_is_normalised(client):
    r = register(client, email="  Alice@Example.COM ")
    assert r.json()["email"] == "alice@example.com"
    assert register(client).status_code == 409
    assert login(client, email="ALICE@example.com").status_code == 200


@pytest.mark.parametrize(
    "body",
    [
        {"email": "alice@example.com", "password": "short"},
        {"email": "alice@example.com", "password": "x" * 73},
        {"email": "alice@example.com", "password": "é" * 37},  # 74 bytes, 37 characters
        {"email": "not-an-email", "password": "long enough"},
        {"password": "long enough"},
        {"email": "alice@example.com"},
        {"email": 1, "password": "long enough"},
        [],
    ],
)
def test_invalid_input(client, body):
    for path in ("/register", "/login"):
        r = client.post(path, json=body)
        assert r.status_code == 422
        assert r.json()["error"] == "invalid_input"
        assert set(r.json()) == {"error", "message"}


def test_password_limits_are_inclusive(client):
    assert register(client, password="12345678").status_code == 201
    assert register(client, email="b@example.com", password="x" * 72).status_code == 201


def test_non_json_body(client):
    r = client.post("/register", content=b"nope", headers={"content-type": "application/json"})
    assert r.status_code == 422 and r.json()["error"] == "invalid_input"


# --- login ----------------------------------------------------------------------------------


def test_login_response(client):
    register(client)
    r = login(client)
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"access_token", "token_type", "expires_in"}
    assert body["token_type"] == "Bearer" and body["expires_in"] == 900


def test_wrong_password_and_unknown_email_are_indistinguishable(client):
    register(client)
    wrong = login(client, password="wrong password")
    unknown = login(client, email="nobody@example.com")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()
    assert wrong.json()["error"] == "invalid_credentials"
    assert set(wrong.json()) == {"error", "message"}


def test_ttl_is_configurable(client, monkeypatch, key_file):
    monkeypatch.setenv("TOKEN_TTL_SECONDS", "60")
    other = TestClient(create(Settings(service_name="auth-service")))
    other.post("/register", json=CREDS)
    assert other.post("/login", json=CREDS).json()["expires_in"] == 60


# --- token ----------------------------------------------------------------------------------


def test_token_claims_header_and_signature(client, key_file):
    user = register(client).json()
    token = login(client).json()["access_token"]
    jwks = keys.jwks(key_file[1])

    header = jwt.get_unverified_header(token)
    assert header["alg"] == "RS256" and header["kid"] == jwks["keys"][0]["kid"]

    public_key = jwt.PyJWK(jwks["keys"][0]).key
    claims = jwt.decode(token, public_key, algorithms=["RS256"], audience="envoy-demo", issuer="http://auth-service")
    assert claims["sub"] == user["id"]
    assert claims["email"] == "alice@example.com"
    assert claims["exp"] - claims["iat"] == 900


def test_issuer_and_audience_are_configurable(key_file, monkeypatch):
    monkeypatch.setenv("JWT_PRIVATE_KEY_PATH", str(key_file[0]))
    monkeypatch.setenv("BCRYPT_ROUNDS", "4")
    monkeypatch.setenv("JWT_ISSUER", "https://issuer.example")
    monkeypatch.setenv("JWT_AUDIENCE", "my-aud")
    client = TestClient(create(Settings(service_name="auth-service")))
    client.post("/register", json=CREDS)
    token = client.post("/login", json=CREDS).json()["access_token"]
    claims = jwt.decode(token, options={"verify_signature": False})
    assert claims["iss"] == "https://issuer.example" and claims["aud"] == "my-aud"


def test_missing_key_file_falls_back_to_throwaway_key(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("JWT_PRIVATE_KEY_PATH", str(tmp_path / "missing.pem"))
    monkeypatch.setenv("BCRYPT_ROUNDS", "4")
    client = TestClient(create(Settings(service_name="auth-service")))
    assert "signing_key_missing" in capsys.readouterr().out
    client.post("/register", json=CREDS)
    assert client.post("/login", json=CREDS).status_code == 200


# --- kid / JWKS -----------------------------------------------------------------------------


def test_kid_is_rfc7638_thumbprint():
    # Test vector from RFC 7638 section 3.1
    n = (
        "0vx7agoebGcQSuuPiLJXZptN9nndrQmbXEps2aiAFbWhM78LhWx4cbbfAAtVT86zwu1RK7aPFFxuhDR1L6tSoc_BJECP"
        "ebWKRXjBZCiFV4n3oknjhMstn64tZ_2W-5JsGY4Hc5n9yBXArwl93lqt7_RN5w6Cf0h4QyQ5v-65YGjQR0_FDW2QvzqY"
        "368QQMicAtaSqzs8KJZgnYb9c7d0zgdAZHzu6qMQvRL5hajrn1n91CbOpbISD08qNLyrdkt-bFTWhAI4vMQFh6WeZu0f"
        "M4lFd2NcRwr3XPksINHaQ-G_xBniIqbw0Ls1jF44-csFCur-kEgU8awapJzKnqDKgw"
    )
    from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers

    def num(s):
        return int.from_bytes(base64.urlsafe_b64decode(s + "=" * (-len(s) % 4)), "big")

    class FakeKey:
        def public_key(self):
            return self

        def public_numbers(self):
            return RSAPublicNumbers(num("AQAB"), num(n))

    assert keys.public_jwk(FakeKey())["kid"] == "NzbLsXh8uDCcd-6MNwXF4W_7noWXFZAfHkxZsRGC9Xs"


def test_generated_key_files_round_trip(tmp_path):
    import subprocess
    import sys

    subprocess.run([sys.executable, "-m", "app.keys", str(tmp_path)], check=True, capture_output=True)
    private = keys.load_private_key(str(tmp_path / "jwt-private.pem"))
    assert json.loads((tmp_path / "jwks.json").read_text()) == keys.jwks(private)
    assert isinstance(private, rsa.RSAPrivateKey)


# --- nothing else is served ---------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    ["/me", "/docs", "/redoc", "/openapi.json", "/debug/request", "/.well-known/jwks.json", "/metrics", "/jwks.json"],
)
def test_nothing_else_is_served(client, path):
    r = client.get(path)
    assert r.status_code == 404
    assert r.json() == {"error": "not_found", "message": "Not found"}


def test_wrong_method_is_405_in_error_shape(client):
    r = client.get("/login")
    assert r.status_code == 405
    assert r.json() == {"error": "method_not_allowed", "message": "Method not allowed"}


def test_faults_are_not_available(client):
    assert client.post("/login?fail=503", json=CREDS).status_code == 401  # ignored, normal handling


class TestCommonBehaviour(CommonBehaviourTests):
    service_name = "auth-service"
    sample_path = "/healthz"

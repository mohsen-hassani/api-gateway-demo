import asyncio
import os
import re
import time
import uuid
from pathlib import Path

import bcrypt
import jwt
from fastapi import Request

from common import jsonlog
from common.app import create_app
from common.errors import ApiError
from common.settings import Settings

from . import keys

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# Compared against when the email is unknown, so both failures cost the same time.
_DUMMY_HASH = bcrypt.hashpw(b"not-a-real-password", bcrypt.gensalt(rounds=4))


def create(settings: Settings | None = None):
    settings = settings or Settings.from_env("auth-service")
    app = create_app(
        settings,
        debug_endpoint=False,
        faults=False,
        metrics=False,
        error_path=False,
        docs=False,
    )

    issuer = os.environ.get("JWT_ISSUER", "http://auth-service")
    audience = os.environ.get("JWT_AUDIENCE", "envoy-demo")
    ttl = int(os.environ.get("TOKEN_TTL_SECONDS", "900"))
    rounds = int(os.environ.get("BCRYPT_ROUNDS", "12"))
    key_path = os.environ.get("JWT_PRIVATE_KEY_PATH", "/keys/jwt-private.pem")

    if Path(key_path).is_file():
        private_key = keys.load_private_key(key_path)
    else:
        private_key = keys.generate_private_key()
        jsonlog.log(
            "warning",
            event="signing_key_missing",
            message=f"{key_path} not found: generated a throwaway key. "
            "Tokens will not match any published JWKS. Run `make keys`.",
        )
    kid = keys.public_jwk(private_key)["kid"]
    private_pem = keys.private_key_pem(private_key)

    users: dict[str, dict] = {}  # normalised email -> {"id", "hash"}
    app.state.users = users

    async def credentials(request: Request) -> tuple[str, str]:
        try:
            body = await request.json()
        except ValueError:
            body = None
        if not isinstance(body, dict):
            raise ApiError(422, "invalid_input", "Body must be a JSON object with email and password")
        email, password = body.get("email"), body.get("password")
        if not isinstance(email, str) or not isinstance(password, str):
            raise ApiError(422, "invalid_input", "email and password are required strings")
        email = email.strip().lower()
        if len(email) > 254 or not EMAIL_RE.match(email):
            raise ApiError(422, "invalid_input", "email is not a valid address")
        if len(password) < 8:
            raise ApiError(422, "invalid_input", "password must be at least 8 characters")
        if len(password.encode()) > 72:
            raise ApiError(422, "invalid_input", "password must be at most 72 bytes")
        return email, password

    @app.post("/register", status_code=201)
    async def register(request: Request):
        email, password = await credentials(request)
        if email in users:
            raise ApiError(409, "email_taken", "An account with this email already exists")
        hashed = await asyncio.to_thread(
            bcrypt.hashpw, password.encode(), bcrypt.gensalt(rounds=rounds)
        )
        if email in users:  # registered while we were hashing
            raise ApiError(409, "email_taken", "An account with this email already exists")
        user = {"id": str(uuid.uuid4()), "hash": hashed}
        users[email] = user
        return {"id": user["id"], "email": email}

    @app.post("/login")
    async def login(request: Request):
        email, password = await credentials(request)
        user = users.get(email)
        valid = await asyncio.to_thread(
            bcrypt.checkpw, password.encode(), user["hash"] if user else _DUMMY_HASH
        )
        if not user or not valid:
            raise ApiError(401, "invalid_credentials", "Invalid email or password")
        now = int(time.time())
        token = jwt.encode(
            {
                "iss": issuer,
                "aud": audience,
                "sub": user["id"],
                "email": email,
                "iat": now,
                "exp": now + ttl,
            },
            private_pem,
            algorithm="RS256",
            headers={"kid": kid},
        )
        return {"access_token": token, "token_type": "Bearer", "expires_in": ttl}

    return app


app = create()

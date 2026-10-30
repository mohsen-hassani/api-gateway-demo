"""Signing key handling: load or generate the RSA key, and build the JWKS.

Run as ``python -m app.keys <output-dir>`` to write ``jwt-private.pem`` and ``jwks.json``
(this is what ``make keys`` does, inside the auth-service image).
"""
import base64
import hashlib
import json
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def _b64url(number: int) -> str:
    raw = number.to_bytes((number.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def generate_private_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def load_private_key(path: str) -> rsa.RSAPrivateKey:
    return serialization.load_pem_private_key(Path(path).read_bytes(), password=None)


def private_key_pem(key: rsa.RSAPrivateKey) -> bytes:
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )


def public_jwk(key: rsa.RSAPrivateKey) -> dict:
    numbers = key.public_key().public_numbers()
    n, e = _b64url(numbers.n), _b64url(numbers.e)
    # RFC 7638: SHA-256 over the required members in lexicographic order, no whitespace
    canonical = json.dumps({"e": e, "kty": "RSA", "n": n}, separators=(",", ":"))
    kid = base64.urlsafe_b64encode(hashlib.sha256(canonical.encode()).digest()).rstrip(b"=").decode()
    return {"kty": "RSA", "use": "sig", "alg": "RS256", "kid": kid, "n": n, "e": e}


def jwks(key: rsa.RSAPrivateKey) -> dict:
    return {"keys": [public_jwk(key)]}


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "/keys")
    out.mkdir(parents=True, exist_ok=True)
    new_key = generate_private_key()
    (out / "jwt-private.pem").write_bytes(private_key_pem(new_key))
    (out / "jwt-private.pem").chmod(0o644)  # dev key; the container runs as another uid
    (out / "jwks.json").write_text(json.dumps(jwks(new_key), indent=2) + "\n")
    print(f"wrote {out}/jwt-private.pem and {out}/jwks.json (kid {public_jwk(new_key)['kid']})")

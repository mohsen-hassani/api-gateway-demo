"""Verify an RS256 JWT against a JWKS file. Used by scripts/auth-contract-test.sh, which runs
it inside the auth-service image (it has PyJWT and cryptography).

Usage: verify_jwt.py <jwks.json> <token> <issuer> <audience>

Prints {"header": ..., "claims": ...} and exits 0 when the token has a kid that is in the
JWKS, the signature verifies, and iss, aud and exp are valid. Otherwise prints the reason to
stderr and exits 1.
"""
import json
import sys

import jwt


def main(argv):
    if len(argv) != 5:
        print(__doc__, file=sys.stderr)
        return 2
    jwks_path, token, issuer, audience = argv[1:]
    with open(jwks_path) as handle:
        jwks = json.load(handle)
    try:
        header = jwt.get_unverified_header(token)
        if header.get("alg") != "RS256":
            raise ValueError(f"alg is {header.get('alg')!r}, expected RS256")
        kid = header.get("kid")
        if not kid:
            raise ValueError("token header has no kid")
        matching = [key for key in jwks.get("keys", []) if key.get("kid") == kid]
        if not matching:
            raise ValueError(f"kid {kid!r} is not in the JWKS")
        claims = jwt.decode(
            token,
            jwt.PyJWK(matching[0]).key,
            algorithms=["RS256"],
            audience=audience,
            issuer=issuer,
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
        )
    except Exception as exc:  # noqa: BLE001 - report any failure as a reason
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"header": header, "claims": claims}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

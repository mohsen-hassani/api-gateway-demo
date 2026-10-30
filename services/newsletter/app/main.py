import re

from fastapi import Request
from pydantic import BaseModel, field_validator

from common.app import create_app
from common.errors import ApiError
from common.settings import Settings

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class UnsubscribeIn(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def _valid_email(cls, value: str) -> str:
        value = value.strip().lower()
        if len(value) > 254 or not EMAIL_RE.match(value):
            raise ValueError("not a valid email address")
        return value


def create(settings: Settings | None = None):
    settings = settings or Settings.from_env("newsletter-service")
    app = create_app(settings)
    unsubscribed_emails: set[str] = set()
    unsubscribed_tokens: set[str] = set()
    app.state.unsubscribed_emails = unsubscribed_emails
    done = {"status": "unsubscribed", "message": "You have been unsubscribed from the newsletter."}

    @app.get("/unsubscribe")
    async def unsubscribe_by_token(request: Request):
        token = request.query_params.get("token", "").strip()
        if not token:
            raise ApiError(422, "invalid_input", "token: a non-empty token is required")
        unsubscribed_tokens.add(token)
        return done

    @app.post("/unsubscribe")
    async def unsubscribe_by_email(body: UnsubscribeIn):
        unsubscribed_emails.add(body.email)
        return done

    return app


app = create()

import contextvars
import json
import sys
from datetime import datetime, timezone

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
# service / version / instance for the request being handled, set by the middleware
context_var: contextvars.ContextVar[dict] = contextvars.ContextVar("log_context", default={})


def log(level: str = "info", **fields) -> None:
    """Write one JSON line to stdout."""
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "level": level,
        **context_var.get(),
        **fields,
    }
    record.setdefault("request_id", request_id_var.get())
    sys.stdout.write(json.dumps(record) + "\n")
    sys.stdout.flush()

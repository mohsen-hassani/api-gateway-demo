import os
import socket
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    service_name: str
    version: str = "v1"
    fail_rate: float = 0.0
    instance: str = field(default_factory=socket.gethostname)

    @classmethod
    def from_env(cls, service_name: str) -> "Settings":
        return cls(
            service_name=service_name,
            version=os.environ.get("APP_VERSION", "v1"),
            fail_rate=float(os.environ.get("FAIL_RATE", "0") or 0),
        )

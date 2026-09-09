"""Non-secret runtime configuration from environment variables."""

from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class RuntimeConfig:
    environment: str = "development"
    data_dir: str = "data"
    max_retries: int = 3
    allowed_actions: tuple[str, ...] = ("export_resume",)

    @classmethod
    def from_env(cls) -> "RuntimeConfig":
        raw_retries = os.getenv("JOB_SEARCH_MAX_RETRIES", "3")
        try:
            retries = int(raw_retries)
        except ValueError as exc:
            raise ValueError("JOB_SEARCH_MAX_RETRIES must be an integer") from exc
        if retries < 1:
            raise ValueError("JOB_SEARCH_MAX_RETRIES must be at least 1")
        actions = tuple(item.strip() for item in os.getenv("JOB_SEARCH_ALLOWED_ACTIONS", "export_resume").split(",") if item.strip())
        return cls(
            environment=os.getenv("JOB_SEARCH_ENV", "development"),
            data_dir=os.getenv("JOB_SEARCH_DATA_DIR", "data"),
            max_retries=retries,
            allowed_actions=actions,
        )


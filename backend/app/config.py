"""Runtime configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE_PATH = BACKEND_ROOT / "data" / "app.db"


@dataclass(frozen=True)
class Settings:
    database_url: str
    youtube_proxy_url: str | None
    openai_api_key: str | None
    openai_model: str


def get_settings(database_url: str | None = None) -> Settings:
    url = database_url or os.environ.get("DATABASE_URL")
    if not url:
        url = f"sqlite:///{DEFAULT_DATABASE_PATH}"
    proxy = os.environ.get("YOUTUBE_PROXY_URL", "").strip() or None
    api_key = os.environ.get("OPENAI_API_KEY", "").strip() or None
    model = os.environ.get("OPENAI_MODEL", "").strip() or "gpt-4o-mini"
    return Settings(
        database_url=url,
        youtube_proxy_url=proxy,
        openai_api_key=api_key,
        openai_model=model,
    )

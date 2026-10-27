"""Look up a video title without downloading the video."""

from __future__ import annotations

import logging

import httpx

from app.services.youtube import canonical_watch_url

logger = logging.getLogger(__name__)


class OEmbedTitleLookup:
    def __init__(self, client: httpx.Client | None = None):
        self._client = client

    def __call__(self, video_id: str) -> str | None:
        url = "https://www.youtube.com/oembed"
        params = {"url": canonical_watch_url(video_id), "format": "json"}
        try:
            if self._client is not None:
                response = self._client.get(url, params=params)
            else:
                response = httpx.get(url, params=params, timeout=8.0, follow_redirects=True)
        except httpx.HTTPError:
            logger.info("oEmbed title lookup failed for %s", video_id, exc_info=True)
            return None
        if response.status_code != 200:
            logger.info("oEmbed title lookup returned %s for %s", response.status_code, video_id)
            return None
        try:
            payload = response.json()
        except ValueError:
            return None
        title = payload.get("title") if isinstance(payload, dict) else None
        if isinstance(title, str) and title.strip():
            return title.strip()
        return None

"""Fetch English captions for a YouTube video without downloading the video."""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

import requests
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    AgeRestricted,
    InvalidVideoId,
    IpBlocked,
    NoTranscriptFound,
    PoTokenRequired,
    RequestBlocked,
    TranscriptsDisabled,
    VideoUnavailable,
    VideoUnplayable,
    YouTubeTranscriptApiException,
)
from youtube_transcript_api.proxies import GenericProxyConfig

from app.errors import AppError
from app.services.segmenter import Cue

logger = logging.getLogger(__name__)

PREFERRED_ENGLISH: tuple[str, ...] = (
    "en",
    "en-US",
    "en-GB",
    "en-CA",
    "en-AU",
    "en-IN",
    "en-IE",
    "en-NZ",
    "en-ZA",
    "en-SG",
)

_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_YOUTUBE_HOSTS = {
    "youtube.com",
    "youtu.be",
    "youtube-nocookie.com",
    "music.youtube.com",
}
_PATH_PREFIXES = {"embed", "shorts", "live", "v"}

MSG_INVALID_URL = "請貼上有效的 YouTube 影片網址。"
MSG_NO_ENGLISH = "這支影片沒有可用的英文字幕（含手動字幕與自動產生字幕）。"
MSG_DISABLED = "這支影片已關閉字幕，無法取得逐字稿。"
MSG_UNAVAILABLE = "找不到這支 YouTube 影片，或影片已無法觀看。"
MSG_AGE = "這支影片有年齡限制，目前無法取得字幕。"
MSG_BLOCKED = (
    "無法從 YouTube 取得字幕。這台伺服器的 IP 可能被 YouTube 擋住了。"
    "請稍後再試，或設定環境變數 YOUTUBE_PROXY_URL 後重試。"
)
MSG_UNREACHABLE = "連線 YouTube 失敗，請稍後再試。"
MSG_GENERIC = "取得字幕時發生錯誤，請稍後再試。"
MSG_EMPTY = "字幕裡沒有可用的英文口語內容。"


@dataclass(frozen=True)
class EnglishTranscript:
    video_id: str
    language_code: str
    caption_source: str
    cues: list[Cue]


class TimeoutSession(requests.Session):
    def __init__(self, timeout: float = 20.0):
        super().__init__()
        self._timeout = timeout

    def request(self, method, url, **kwargs):  # type: ignore[override]
        kwargs.setdefault("timeout", self._timeout)
        return super().request(method, url, **kwargs)


def parse_youtube_video_id(url: str) -> str | None:
    raw = url.strip()
    if _VIDEO_ID.fullmatch(raw):
        return raw
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    host = parsed.netloc.lower()
    if "@" in host:
        host = host.split("@", 1)[1]
    if ":" in host:
        host = host.split(":", 1)[0]
    if host.startswith("www."):
        host = host[4:]
    if host.startswith("m."):
        host = host[2:]
    if host not in _YOUTUBE_HOSTS:
        return None
    if host == "youtu.be":
        video_id = parsed.path.strip("/").split("/")[0]
        return video_id if _VIDEO_ID.fullmatch(video_id) else None
    query = parse_qs(parsed.query)
    if "v" in query and query["v"] and _VIDEO_ID.fullmatch(query["v"][0]):
        return query["v"][0]
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 2 and parts[0] in _PATH_PREFIXES and _VIDEO_ID.fullmatch(parts[1]):
        return parts[1]
    return None


def canonical_watch_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def _is_english(language_code: str) -> bool:
    code = language_code.lower()
    return code == "en" or code.startswith("en-")


def _first_english(transcripts: Iterable, *, generated: bool):
    for transcript in transcripts:
        if bool(transcript.is_generated) == generated and _is_english(transcript.language_code):
            return transcript
    return None


def choose_english_transcript(transcript_list):
    """Prefer manually created English captions, then auto-generated English."""
    try:
        return transcript_list.find_manually_created_transcript(PREFERRED_ENGLISH), "manual"
    except NoTranscriptFound:
        manual = _first_english(transcript_list, generated=False)
        if manual is not None:
            return manual, "manual"
    try:
        return transcript_list.find_generated_transcript(PREFERRED_ENGLISH), "generated"
    except NoTranscriptFound:
        generated = _first_english(transcript_list, generated=True)
        if generated is not None:
            return generated, "generated"
    video_id = getattr(transcript_list, "video_id", "")
    raise NoTranscriptFound(video_id, PREFERRED_ENGLISH, transcript_list)


def map_youtube_error(exc: Exception) -> AppError:
    if isinstance(exc, AppError):
        return exc
    if isinstance(exc, (IpBlocked, RequestBlocked, PoTokenRequired)):
        return AppError(503, "youtube_blocked", MSG_BLOCKED)
    if isinstance(exc, TranscriptsDisabled):
        return AppError(422, "transcripts_disabled", MSG_DISABLED)
    if isinstance(exc, (VideoUnavailable, VideoUnplayable, InvalidVideoId)):
        return AppError(404, "video_unavailable", MSG_UNAVAILABLE)
    if isinstance(exc, AgeRestricted):
        return AppError(422, "age_restricted", MSG_AGE)
    if isinstance(exc, NoTranscriptFound):
        return AppError(422, "no_english_captions", MSG_NO_ENGLISH)
    if isinstance(exc, requests.RequestException):
        return AppError(503, "youtube_unreachable", MSG_UNREACHABLE)
    if isinstance(exc, YouTubeTranscriptApiException):
        return AppError(502, "transcript_failed", MSG_GENERIC)
    return AppError(502, "transcript_failed", MSG_GENERIC)


def build_youtube_api(proxy_url: str | None = None) -> YouTubeTranscriptApi:
    session = TimeoutSession()
    if proxy_url:
        proxy = GenericProxyConfig(http_url=proxy_url, https_url=proxy_url)
        return YouTubeTranscriptApi(proxy_config=proxy, http_client=session)
    return YouTubeTranscriptApi(http_client=session)


class YoutubeTranscriptFetcher:
    def __init__(self, api_factory=None, proxy_url: str | None = None):
        self._api_factory = api_factory or (lambda: build_youtube_api(proxy_url))

    def fetch_english(self, video_id: str) -> EnglishTranscript:
        api = self._api_factory()
        try:
            listing = api.list(video_id)
        except (YouTubeTranscriptApiException, requests.RequestException) as exc:
            logger.warning("YouTube transcript list failed for %s: %s", video_id, type(exc).__name__)
            raise map_youtube_error(exc) from exc
        try:
            transcript, source = choose_english_transcript(listing)
        except NoTranscriptFound as exc:
            raise map_youtube_error(exc) from exc
        try:
            fetched = transcript.fetch()
        except (YouTubeTranscriptApiException, requests.RequestException) as exc:
            logger.warning("YouTube transcript fetch failed for %s: %s", video_id, type(exc).__name__)
            raise map_youtube_error(exc) from exc
        cues = [
            Cue(text=snippet.text, start=float(snippet.start), duration=float(snippet.duration))
            for snippet in fetched
        ]
        return EnglishTranscript(
            video_id=video_id,
            language_code=fetched.language_code,
            caption_source=source,
            cues=cues,
        )


def require_video_id(url: str) -> str:
    video_id = parse_youtube_video_id(url)
    if video_id is None:
        raise AppError(400, "invalid_url", MSG_INVALID_URL)
    return video_id

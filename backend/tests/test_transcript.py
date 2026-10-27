"""YouTube URL parsing, caption selection, and error mapping."""

import pytest
import requests
from youtube_transcript_api import FetchedTranscript, FetchedTranscriptSnippet
from youtube_transcript_api._errors import (
    AgeRestricted,
    IpBlocked,
    NoTranscriptFound,
    RequestBlocked,
    TranscriptsDisabled,
    VideoUnavailable,
)

from app.errors import AppError
from app.services.youtube import (
    YoutubeTranscriptFetcher,
    choose_english_transcript,
    map_youtube_error,
    parse_youtube_video_id,
)

VIDEO_ID = "lC_-9TD3TfA"
WATCH = f"https://www.youtube.com/watch?v={VIDEO_ID}"


@pytest.mark.parametrize(
    "url",
    [
        WATCH,
        f"  {WATCH}  ",
        f"https://www.youtube.com/watch?v={VIDEO_ID}&t=30s",
        f"https://www.youtube.com/watch?list=abc&v={VIDEO_ID}",
        f"https://m.youtube.com/watch?v={VIDEO_ID}",
        f"https://youtu.be/{VIDEO_ID}",
        f"https://youtu.be/{VIDEO_ID}?t=12",
        f"https://www.youtube.com/embed/{VIDEO_ID}",
        f"https://www.youtube.com/shorts/{VIDEO_ID}",
        f"https://www.youtube.com/live/{VIDEO_ID}",
        f"https://www.youtube-nocookie.com/embed/{VIDEO_ID}",
        f"http://youtube.com/watch?v={VIDEO_ID}",
        VIDEO_ID,
    ],
)
def test_parse_youtube_url(url: str):
    assert parse_youtube_video_id(url) == VIDEO_ID


@pytest.mark.parametrize(
    "url",
    [
        "",
        "https://vimeo.com/123456789",
        "https://www.youtube.com/watch?v=short",
        "https://www.youtube.com/playlist?list=abc",
        "not a url",
        f"https://example.com/watch?v={VIDEO_ID}",
    ],
)
def test_reject_non_youtube_url(url: str):
    assert parse_youtube_video_id(url) is None


class _Transcript:
    def __init__(self, language_code: str, generated: bool, text: str = "Hello there."):
        self.language_code = language_code
        self.language = "English"
        self.is_generated = generated
        self._text = text

    def fetch(self, preserve_formatting: bool = False) -> FetchedTranscript:
        return FetchedTranscript(
            snippets=[FetchedTranscriptSnippet(text=self._text, start=0.0, duration=6.0)],
            video_id=VIDEO_ID,
            language=self.language,
            language_code=self.language_code,
            is_generated=self.is_generated,
        )


class _Listing:
    def __init__(self, items: list[_Transcript]):
        self.video_id = VIDEO_ID
        self._items = items

    def __iter__(self):
        return iter(self._items)

    def __str__(self) -> str:
        return "fake transcripts"

    def find_manually_created_transcript(self, codes):
        return self._find(codes, generated=False)

    def find_generated_transcript(self, codes):
        return self._find(codes, generated=True)

    def _find(self, codes, *, generated: bool):
        for code in codes:
            for item in self._items:
                if item.is_generated == generated and item.language_code == code:
                    return item
        raise NoTranscriptFound(self.video_id, codes, self)


class _Api:
    def __init__(self, listing=None, error: Exception | None = None):
        self._listing = listing
        self._error = error

    def list(self, video_id: str):
        if self._error:
            raise self._error
        return self._listing


def test_prefers_manual_english_over_generated():
    manual = _Transcript("en", generated=False, text="Manual caption.")
    generated = _Transcript("en", generated=True, text="Generated caption.")
    chosen, source = choose_english_transcript(_Listing([generated, manual]))
    assert chosen is manual
    assert source == "manual"


def test_falls_back_to_generated_english():
    generated = _Transcript("en-GB", generated=True, text="Auto caption.")
    chosen, source = choose_english_transcript(_Listing([_Transcript("ja", False), generated]))
    assert chosen is generated
    assert source == "generated"


def test_accepts_english_variant_outside_the_preferred_list():
    manual = _Transcript("en-PH", generated=False)
    chosen, source = choose_english_transcript(_Listing([manual]))
    assert chosen is manual
    assert source == "manual"


def test_fetcher_returns_cues_from_manual_captions():
    listing = _Listing([_Transcript("en", generated=False, text="Hello there.")])
    fetched = YoutubeTranscriptFetcher(api_factory=lambda: _Api(listing)).fetch_english(VIDEO_ID)
    assert fetched.caption_source == "manual"
    assert fetched.language_code == "en"
    assert fetched.cues[0].text == "Hello there."
    assert fetched.cues[0].start == 0.0
    assert fetched.cues[0].duration == 6.0


def test_fetcher_maps_request_blocked():
    fetcher = YoutubeTranscriptFetcher(api_factory=lambda: _Api(error=RequestBlocked(VIDEO_ID)))
    with pytest.raises(AppError) as caught:
        fetcher.fetch_english(VIDEO_ID)
    assert caught.value.status_code == 503
    assert caught.value.code == "youtube_blocked"
    assert "YOUTUBE_PROXY_URL" in caught.value.message


@pytest.mark.parametrize(
    ("exc", "status_code", "code"),
    [
        (IpBlocked(VIDEO_ID), 503, "youtube_blocked"),
        (RequestBlocked(VIDEO_ID), 503, "youtube_blocked"),
        (TranscriptsDisabled(VIDEO_ID), 422, "transcripts_disabled"),
        (VideoUnavailable(VIDEO_ID), 404, "video_unavailable"),
        (AgeRestricted(VIDEO_ID), 422, "age_restricted"),
        (NoTranscriptFound(VIDEO_ID, ["en"], _Listing([])), 422, "no_english_captions"),
        (requests.ConnectionError("nope"), 503, "youtube_unreachable"),
    ],
)
def test_map_youtube_error(exc, status_code, code):
    mapped = map_youtube_error(exc)
    assert mapped.status_code == status_code
    assert mapped.code == code
    assert mapped.message

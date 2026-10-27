"""HTTP API for importing videos and reading segments."""

from fastapi.testclient import TestClient

from app.main import create_app
from app.routers import videos
from app.services.segmenter import Cue
from app.services.youtube import EnglishTranscript

VIDEO_ID = "lC_-9TD3TfA"
OTHER_ID = "dQw4w9WgXcQ"


class FakeFetcher:
    def __init__(self):
        self.calls: list[str] = []

    def fetch_english(self, video_id: str) -> EnglishTranscript:
        self.calls.append(video_id)
        if video_id == OTHER_ID:
            cues = [Cue("Another video starts here.", 0.0, 6.0)]
            source = "generated"
            language = "en-US"
        else:
            cues = [
                Cue("Hello there.", 0.0, 2.0),
                Cue("How are you?", 2.0, 2.0),
                Cue("I am fine today.", 4.0, 2.5),
                Cue("This next thought is its own segment.", 7.0, 8.0),
            ]
            source = "manual"
            language = "en"
        return EnglishTranscript(
            video_id=video_id,
            language_code=language,
            caption_source=source,
            cues=cues,
        )


def _client(fetcher: FakeFetcher, titles: dict[str, str | None] | None = None) -> TestClient:
    app = create_app("sqlite:///:memory:")
    titles = titles if titles is not None else {VIDEO_ID: "Meta Muse Is Incredible", OTHER_ID: None}
    app.dependency_overrides[videos.get_fetcher] = lambda: fetcher
    app.dependency_overrides[videos.get_title_lookup] = lambda: (lambda video_id: titles.get(video_id))
    return TestClient(app)


def test_import_list_and_read_segments():
    fetcher = FakeFetcher()
    client = _client(fetcher)

    created = client.post("/api/videos", json={"url": f"https://www.youtube.com/watch?v={VIDEO_ID}&t=10s"})
    assert created.status_code == 201
    body = created.json()
    assert body["youtube_id"] == VIDEO_ID
    assert body["url"] == f"https://www.youtube.com/watch?v={VIDEO_ID}"
    assert body["title"] == "Meta Muse Is Incredible"
    assert body["caption_source"] == "manual"
    assert body["language_code"] == "en"
    assert body["segment_count"] == 2
    assert body["segments"][0]["position"] == 0
    assert body["segments"][0]["text"] == "Hello there. How are you? I am fine today."
    assert body["segments"][0]["start_time"] == 0.0
    assert body["segments"][0]["end_time"] == 6.5
    assert body["segments"][1]["start_time"] == 7.0
    assert body["segments"][1]["end_time"] == 15.0

    again = client.post("/api/videos", json={"url": f"https://youtu.be/{VIDEO_ID}"})
    assert again.status_code == 200
    assert again.json()["id"] == body["id"]
    assert fetcher.calls == [VIDEO_ID]

    listing = client.get("/api/videos")
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()] == [body["id"]]

    detail = client.get(f"/api/videos/{body['id']}")
    assert detail.status_code == 200
    assert detail.json()["segments"][1]["text"] == "This next thought is its own segment."

    segments = client.get(f"/api/videos/{body['id']}/segments")
    assert segments.status_code == 200
    assert [item["position"] for item in segments.json()] == [0, 1]


def test_second_video_is_listed_first_and_missing_title_is_allowed():
    client = _client(FakeFetcher())
    first = client.post("/api/videos", json={"url": VIDEO_ID})
    second = client.post("/api/videos", json={"url": f"https://youtu.be/{OTHER_ID}"})
    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["title"] is None
    assert second.json()["caption_source"] == "generated"
    listed = client.get("/api/videos").json()
    assert [item["youtube_id"] for item in listed] == [OTHER_ID, VIDEO_ID]


def test_invalid_url_and_missing_video():
    client = _client(FakeFetcher())
    invalid = client.post("/api/videos", json={"url": "https://vimeo.com/123"})
    assert invalid.status_code == 400
    assert invalid.json()["detail"]["code"] == "invalid_url"

    missing = client.get("/api/videos/99")
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "not_found"

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}


def test_blocked_fetcher_is_a_clear_error():
    from app.errors import AppError

    class BlockedFetcher:
        def fetch_english(self, video_id: str):
            raise AppError(
                503,
                "youtube_blocked",
                "無法從 YouTube 取得字幕。請設定 YOUTUBE_PROXY_URL。",
            )

    app = create_app("sqlite:///:memory:")
    app.dependency_overrides[videos.get_fetcher] = lambda: BlockedFetcher()
    app.dependency_overrides[videos.get_title_lookup] = lambda: (lambda _video_id: None)
    client = TestClient(app)
    response = client.post("/api/videos", json={"url": f"https://www.youtube.com/watch?v={VIDEO_ID}"})
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "youtube_blocked"
    assert client.get("/api/videos").json() == []

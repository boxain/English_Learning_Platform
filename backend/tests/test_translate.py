"""Traditional Chinese translation and caching."""

import json

import httpx
import pytest
from sqlalchemy import create_engine, text

from app.config import Settings
from app.db import ensure_schema, make_session_factory
from app.main import create_app
from app.models import Base, Segment, Video
from app.routers import videos
from app.services.translate import (
    SYSTEM_PROMPT,
    OpenAITranslator,
    TranslationError,
    build_translator,
)
from fastapi.testclient import TestClient

from tests.test_api import VIDEO_ID, FakeFetcher, _client

OPENAI_RESPONSE = {
    "choices": [
        {
            "message": {
                "content": json.dumps(
                    {"translations": ["你好。", "今天天氣很好。"]},
                    ensure_ascii=False,
                )
            }
        }
    ]
}


def _settings(**overrides) -> Settings:
    values = {
        "database_url": "sqlite:///:memory:",
        "youtube_proxy_url": None,
        "openai_api_key": None,
        "openai_model": "gpt-4o-mini",
    }
    values.update(overrides)
    return Settings(**values)


def test_build_translator_requires_a_key():
    assert build_translator(_settings()) is None
    translator = build_translator(_settings(openai_api_key="sk-test", openai_model="gpt-4.1-mini"))
    assert isinstance(translator, OpenAITranslator)
    assert translator._model == "gpt-4.1-mini"


def test_openai_translator_parses_traditional_chinese_json():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = json.loads(request.content.decode())
        return httpx.Response(200, json=OPENAI_RESPONSE)

    translator = OpenAITranslator("sk-test", client=httpx.Client(transport=httpx.MockTransport(handler)))
    result = translator.translate_many(["Hello.", "The weather is nice today."])

    assert result == ["你好。", "今天天氣很好。"]
    assert seen["auth"] == "Bearer sk-test"
    assert seen["body"]["model"] == "gpt-4o-mini"
    assert "zh-TW" in seen["body"]["messages"][0]["content"]
    assert seen["body"]["messages"][0]["content"] == SYSTEM_PROMPT
    assert json.loads(seen["body"]["messages"][1]["content"])["segments"] == [
        "Hello.",
        "The weather is nice today.",
    ]


def test_openai_translator_accepts_fenced_json_and_rejects_bad_counts():
    def ok(request: httpx.Request) -> httpx.Response:
        payload = {
            "choices": [
                {"message": {"content": '```json\n{"translations": ["你好。"]}\n```'}}
            ]
        }
        return httpx.Response(200, json=payload)

    translator = OpenAITranslator("sk-test", client=httpx.Client(transport=httpx.MockTransport(ok)))
    assert translator.translate_many(["Hello."]) == ["你好。"]

    def mismatch(request: httpx.Request) -> httpx.Response:
        payload = {"choices": [{"message": {"content": '{"translations": ["只有一句"]}'}}]}
        return httpx.Response(200, json=payload)

    translator = OpenAITranslator("sk-test", client=httpx.Client(transport=httpx.MockTransport(mismatch)))
    with pytest.raises(TranslationError):
        translator.translate_many(["Hello.", "Goodbye."])


def test_openai_http_error_is_a_translation_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "bad key"}})

    translator = OpenAITranslator("sk-test", client=httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(TranslationError, match="401"):
        translator.translate_many(["Hello."])


def test_adds_translation_column_to_an_existing_database(tmp_path):
    database = tmp_path / "old.db"
    engine = create_engine(f"sqlite:///{database}")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE segments (
                    id INTEGER PRIMARY KEY,
                    video_id INTEGER,
                    position INTEGER,
                    text TEXT,
                    start_time FLOAT,
                    end_time FLOAT
                )
                """
            )
        )
    ensure_schema(engine)
    with engine.connect() as connection:
        columns = [row[1] for row in connection.execute(text("PRAGMA table_info(segments)"))]
    assert "translation_zh" in columns
    Base.metadata.create_all(engine)


class RecordingTranslator:
    def __init__(self, fail: bool = False):
        self.calls: list[list[str]] = []
        self.fail = fail

    def translate_many(self, texts: list[str]) -> list[str]:
        self.calls.append(list(texts))
        if self.fail:
            raise TranslationError("offline")
        return [f"譯：{text}" for text in texts]


def _client_with_translator(translator) -> TestClient:
    app = create_app("sqlite:///:memory:")
    app.dependency_overrides[videos.get_fetcher] = lambda: FakeFetcher()
    app.dependency_overrides[videos.get_title_lookup] = lambda: (lambda _video_id: "Title")
    app.dependency_overrides[videos.get_translator] = lambda: translator
    return TestClient(app)


def test_translation_is_cached_and_not_repeated():
    translator = RecordingTranslator()
    client = _client_with_translator(translator)

    created = client.post("/api/videos", json={"url": f"https://www.youtube.com/watch?v={VIDEO_ID}"})
    assert created.status_code == 201
    body = created.json()
    assert body["translation_enabled"] is True
    assert body["segments"][0]["translation_zh"].startswith("譯：")
    assert "Hello there." in body["segments"][0]["translation_zh"]
    assert len(translator.calls) == 1

    again = client.post("/api/videos", json={"url": f"https://youtu.be/{VIDEO_ID}"})
    assert again.status_code == 200
    assert again.json()["segments"][0]["translation_zh"] == body["segments"][0]["translation_zh"]
    detail = client.get(f"/api/videos/{body['id']}/segments")
    assert detail.status_code == 200
    assert detail.json()[1]["translation_zh"].startswith("譯：")
    assert len(translator.calls) == 1


def test_missing_key_keeps_english_practice():
    client = _client(FakeFetcher())
    created = client.post("/api/videos", json={"url": VIDEO_ID})
    assert created.status_code == 201
    body = created.json()
    assert body["translation_enabled"] is False
    assert body["segments"][0]["translation_zh"] is None


def test_translation_failure_does_not_block_import():
    client = _client_with_translator(RecordingTranslator(fail=True))
    created = client.post("/api/videos", json={"url": VIDEO_ID})
    assert created.status_code == 201
    assert created.json()["translation_enabled"] is True
    assert created.json()["segments"][0]["translation_zh"] is None
    assert created.json()["segments"][0]["text"]


def test_backfill_translates_segments_saved_before_a_key_exists():
    app = create_app("sqlite:///:memory:")
    app.dependency_overrides[videos.get_fetcher] = lambda: FakeFetcher()
    app.dependency_overrides[videos.get_title_lookup] = lambda: (lambda _video_id: "Title")
    client = TestClient(app)
    created = client.post("/api/videos", json={"url": VIDEO_ID})
    assert created.json()["segments"][0]["translation_zh"] is None

    translator = RecordingTranslator()
    app.dependency_overrides[videos.get_translator] = lambda: translator
    detail = client.get(f"/api/videos/{created.json()['id']}")
    assert detail.status_code == 200
    assert detail.json()["translation_enabled"] is True
    assert detail.json()["segments"][0]["translation_zh"].startswith("譯：")
    client.get(f"/api/videos/{created.json()['id']}")
    assert len(translator.calls) == 1


def test_session_round_trip_keeps_cached_translation(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'app.db'}")
    ensure_schema(engine)
    session = make_session_factory(engine)()
    video = Video(
        youtube_id=VIDEO_ID,
        url=f"https://www.youtube.com/watch?v={VIDEO_ID}",
        title="Sample",
        caption_source="manual",
        language_code="en",
    )
    video.segments.append(
        Segment(position=0, text="Hello.", translation_zh="你好。", start_time=0.0, end_time=6.0)
    )
    session.add(video)
    session.commit()
    stored = session.get(Segment, video.segments[0].id)
    assert stored is not None
    assert stored.translation_zh == "你好。"
    session.close()

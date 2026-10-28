"""Traditional Chinese translations, cached on each segment."""

from __future__ import annotations

import json
import logging

import httpx

from app.config import Settings
from app.models import Segment, Video

logger = logging.getLogger(__name__)

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_BATCH_SIZE = 12

SYSTEM_PROMPT = (
    "You translate English listening-practice lines into Traditional Chinese (zh-TW) "
    "as used in Taiwan. The audience is learning spoken English. "
    "Preserve names, numbers, and a natural spoken tone. "
    "Do not add explanations, notes, or alternative translations. "
    'Reply with JSON only: {"translations": ["...", ...]} . '
    "The translations array must have the same length and order as the input segments."
)


class TranslationError(Exception):
    """The translator could not return one Traditional Chinese line per segment."""


class OpenAITranslator:
    def __init__(
        self,
        api_key: str,
        *,
        model: str = "gpt-4o-mini",
        client: httpx.Client | None = None,
    ):
        self._api_key = api_key
        self._model = model
        self._client = client

    def translate_many(self, texts: list[str]) -> list[str]:
        if not texts:
            return []
        payload = {
            "model": self._model,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps({"segments": texts}, ensure_ascii=False)},
            ],
        }
        try:
            response = self._post(payload)
        except httpx.HTTPError as exc:
            raise TranslationError("OpenAI request failed") from exc
        if response.status_code != 200:
            raise TranslationError(f"OpenAI returned HTTP {response.status_code}")
        try:
            body = response.json()
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise TranslationError("OpenAI response could not be read") from exc
        translations = _parse_translations(content)
        if len(translations) != len(texts):
            raise TranslationError(
                f"OpenAI returned {len(translations)} translations for {len(texts)} segments"
            )
        return translations

    def _post(self, payload: dict) -> httpx.Response:
        headers = {"Authorization": f"Bearer {self._api_key}"}
        if self._client is not None:
            return self._client.post(OPENAI_URL, headers=headers, json=payload)
        with httpx.Client(timeout=60.0) as client:
            return client.post(OPENAI_URL, headers=headers, json=payload)


def build_translator(settings: Settings) -> OpenAITranslator | None:
    if not settings.openai_api_key:
        return None
    return OpenAITranslator(settings.openai_api_key, model=settings.openai_model)


def _parse_translations(content: str) -> list[str]:
    raw = _strip_code_fence(content)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise TranslationError("OpenAI translation JSON was invalid") from exc
    values = payload.get("translations") if isinstance(payload, dict) else None
    if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
        raise TranslationError("OpenAI translation JSON did not include a string array")
    return [item.strip() for item in values]


def _strip_code_fence(content: str) -> str:
    raw = content.strip()
    if not raw.startswith("```"):
        return raw
    lines = raw.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _needs_translation(segment: Segment) -> bool:
    return not (segment.translation_zh and segment.translation_zh.strip())


def fill_missing_translations(
    video: Video,
    translator: OpenAITranslator | None,
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> bool:
    """Translate segments that have no cached Traditional Chinese. Failures stay untranslated."""
    if translator is None:
        return False
    pending = [segment for segment in video.segments if _needs_translation(segment)]
    if not pending:
        return False
    changed = False
    for start in range(0, len(pending), batch_size):
        chunk = pending[start : start + batch_size]
        changed = _translate_chunk(chunk, translator) or changed
    if changed:
        logger.info("Cached Traditional Chinese for %s segments of video %s", _translated_count(video), video.youtube_id)
    return changed


def _translated_count(video: Video) -> int:
    return sum(1 for segment in video.segments if not _needs_translation(segment))


def _translate_chunk(segments: list[Segment], translator: OpenAITranslator) -> bool:
    try:
        translations = translator.translate_many([segment.text for segment in segments])
    except Exception:
        logger.warning("Batch translation failed for %s segments; retrying one by one", len(segments))
        return _translate_one_by_one(segments, translator)
    if len(translations) != len(segments):
        return _translate_one_by_one(segments, translator)
    changed = False
    for segment, translation in zip(segments, translations, strict=True):
        if translation:
            segment.translation_zh = translation
            changed = True
    return changed


def _translate_one_by_one(segments: list[Segment], translator: OpenAITranslator) -> bool:
    changed = False
    for segment in segments:
        try:
            translations = translator.translate_many([segment.text])
        except TranslationError:
            logger.warning("Translation failed for segment %s", segment.position)
            continue
        except Exception:
            logger.warning("Translation failed for segment %s", segment.position, exc_info=True)
            continue
        if len(translations) == 1 and translations[0]:
            segment.translation_zh = translations[0]
            changed = True
    return changed

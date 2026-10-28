"""Import a YouTube URL: fetch captions, segment them, and store the result."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.errors import AppError
from app.models import Segment, Video
from app.services.segmenter import segment_transcript
from app.services.translate import OpenAITranslator, fill_missing_translations
from app.services.youtube import MSG_EMPTY, EnglishTranscript, YoutubeTranscriptFetcher, canonical_watch_url, require_video_id


def import_video(
    db: Session,
    url: str,
    *,
    fetcher: YoutubeTranscriptFetcher,
    title_lookup: Callable[[str], str | None],
    translator: OpenAITranslator | None = None,
) -> tuple[Video, bool]:
    video_id = require_video_id(url)
    existing = db.scalar(
        select(Video).where(Video.youtube_id == video_id).options(selectinload(Video.segments))
    )
    if existing is not None:
        store_translations(db, existing, translator)
        return existing, False

    transcript: EnglishTranscript = fetcher.fetch_english(video_id)
    drafts = segment_transcript(transcript.cues)
    if not drafts:
        raise AppError(422, "no_spoken_content", MSG_EMPTY)

    video = Video(
        youtube_id=video_id,
        url=canonical_watch_url(video_id),
        title=title_lookup(video_id),
        caption_source=transcript.caption_source,
        language_code=transcript.language_code,
    )
    for position, draft in enumerate(drafts):
        video.segments.append(
            Segment(
                position=position,
                text=draft.text,
                start_time=draft.start_time,
                end_time=draft.end_time,
            )
        )
    db.add(video)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(video)
    store_translations(db, video, translator)
    return video, True


def store_translations(db: Session, video: Video, translator: OpenAITranslator | None) -> None:
    if not fill_missing_translations(video, translator):
        return
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(video)

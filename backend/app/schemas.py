"""API request and response models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import Segment, Video


class VideoCreate(BaseModel):
    url: str = Field(min_length=1, max_length=500)


class SegmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    position: int
    text: str
    start_time: float
    end_time: float

    @classmethod
    def from_segment(cls, segment: Segment) -> SegmentOut:
        return cls(
            id=segment.id,
            position=segment.position,
            text=segment.text,
            start_time=segment.start_time,
            end_time=segment.end_time,
        )


class VideoOut(BaseModel):
    id: int
    youtube_id: str
    url: str
    title: str | None
    caption_source: str
    language_code: str
    created_at: datetime
    segment_count: int

    @classmethod
    def from_video(cls, video: Video) -> VideoOut:
        return cls(
            id=video.id,
            youtube_id=video.youtube_id,
            url=video.url,
            title=video.title,
            caption_source=video.caption_source,
            language_code=video.language_code,
            created_at=video.created_at,
            segment_count=len(video.segments),
        )


class VideoDetail(VideoOut):
    segments: list[SegmentOut]

    @classmethod
    def from_video(cls, video: Video) -> VideoDetail:
        base = VideoOut.from_video(video)
        return cls(
            **base.model_dump(),
            segments=[SegmentOut.from_segment(segment) for segment in video.segments],
        )

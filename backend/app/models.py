"""SQLite tables for videos and practice segments."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    youtube_id: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    url: Mapped[str] = mapped_column(String(300))
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    caption_source: Mapped[str] = mapped_column(String(16))
    language_code: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    segments: Mapped[list[Segment]] = relationship(
        back_populates="video",
        cascade="all, delete-orphan",
        order_by="Segment.position",
    )


class Segment(Base):
    __tablename__ = "segments"
    __table_args__ = (UniqueConstraint("video_id", "position", name="uq_segment_position"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    start_time: Mapped[float] = mapped_column(Float)
    end_time: Mapped[float] = mapped_column(Float)

    video: Mapped[Video] = relationship(back_populates="segments")

"""Video and segment HTTP endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import session_scope
from app.models import Video
from app.schemas import SegmentOut, VideoCreate, VideoDetail, VideoOut
from app.services.importer import import_video

router = APIRouter(prefix="/api/videos", tags=["videos"])


def get_db(request: Request):
    yield from session_scope(request.app.state.session_factory)


def get_fetcher(request: Request):
    return request.app.state.fetcher_factory()


def get_title_lookup(request: Request):
    return request.app.state.title_lookup_factory()


def _load_video(db: Session, video_id: int) -> Video:
    video = db.scalar(
        select(Video).where(Video.id == video_id).options(selectinload(Video.segments))
    )
    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "找不到這支影片。"},
        )
    return video


@router.get("", response_model=list[VideoOut])
def list_videos(db: Session = Depends(get_db)) -> list[VideoOut]:
    videos = db.scalars(
        select(Video).options(selectinload(Video.segments)).order_by(Video.created_at.desc(), Video.id.desc())
    ).all()
    return [VideoOut.from_video(video) for video in videos]


@router.post("", response_model=VideoDetail)
def create_video(
    payload: VideoCreate,
    response: Response,
    db: Session = Depends(get_db),
    fetcher=Depends(get_fetcher),
    title_lookup=Depends(get_title_lookup),
) -> VideoDetail:
    video, created = import_video(db, payload.url, fetcher=fetcher, title_lookup=title_lookup)
    video = _load_video(db, video.id)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return VideoDetail.from_video(video)


@router.get("/{video_id}", response_model=VideoDetail)
def get_video(video_id: int, db: Session = Depends(get_db)) -> VideoDetail:
    return VideoDetail.from_video(_load_video(db, video_id))


@router.get("/{video_id}/segments", response_model=list[SegmentOut])
def list_segments(video_id: int, db: Session = Depends(get_db)) -> list[SegmentOut]:
    video = _load_video(db, video_id)
    return [SegmentOut.from_segment(segment) for segment in video.segments]

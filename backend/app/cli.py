"""Import one YouTube URL from the command line.

Example:
    python -m app.cli "https://www.youtube.com/watch?v=lC_-9TD3TfA"
"""

from __future__ import annotations

import argparse
import logging
import sys

from app.config import get_settings
from app.db import ensure_schema, make_engine, make_session_factory
from app.errors import AppError
from app.services.importer import import_video
from app.services.titles import OEmbedTitleLookup
from app.services.translate import build_translator
from app.services.youtube import YoutubeTranscriptFetcher


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch an English transcript and store shadowing segments.")
    parser.add_argument("url", help="YouTube video URL")
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO)
    args = build_parser().parse_args(argv)
    settings = get_settings()
    engine = make_engine(settings)
    ensure_schema(engine)
    session = make_session_factory(engine)()
    try:
        video, created = import_video(
            session,
            args.url,
            fetcher=YoutubeTranscriptFetcher(proxy_url=settings.youtube_proxy_url),
            title_lookup=OEmbedTitleLookup(),
            translator=build_translator(settings),
        )
        lines = []
        for segment in video.segments[:8]:
            lines.append(
                f"  #{segment.position:03d} "
                f"{segment.start_time:7.2f}-{segment.end_time:7.2f}s  {segment.text}"
            )
            if segment.translation_zh:
                lines.append(f"         {segment.translation_zh}")
        remaining = len(video.segments) - 8
        summary = (
            f"{'imported' if created else 'already stored'}: "
            f"id={video.id} youtube_id={video.youtube_id} title={video.title or '(no title)'}\n"
            f"captions={video.caption_source} language={video.language_code} "
            f"segments={len(video.segments)}"
        )
    except AppError as exc:
        print(f"error [{exc.code}]: {exc.message}", file=sys.stderr)
        return 1
    finally:
        session.close()

    print(summary)
    for line in lines:
        print(line)
    if remaining > 0:
        print(f"  ... {remaining} more segments")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

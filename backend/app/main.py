"""FastAPI application entrypoint."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.db import ensure_schema, make_engine, make_session_factory
from app.errors import AppError
from app.routers import videos
from app.services.titles import OEmbedTitleLookup
from app.services.translate import build_translator
from app.services.youtube import YoutubeTranscriptFetcher


def create_app(database_url: str | None = None) -> FastAPI:
    settings = get_settings(database_url)
    engine = make_engine(settings)
    session_factory = make_session_factory(engine)
    ensure_schema(engine)

    app = FastAPI(title="English Learning Platform API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.fetcher_factory = lambda: YoutubeTranscriptFetcher(proxy_url=settings.youtube_proxy_url)
    app.state.title_lookup_factory = OEmbedTitleLookup
    app.state.translator_factory = lambda: build_translator(settings)

    @app.exception_handler(AppError)
    def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": {"code": exc.code, "message": exc.message}},
        )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(videos.router)
    return app


app = create_app()


def main() -> None:
    import uvicorn

    logging.basicConfig(level=logging.INFO)
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()

"""SkillGraph ASGI application."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.db import make_engine, make_session_factory, run_migrations
from app.errors import DomainError
from app.seed import seed_if_empty
from app.services.catalog import GraphCache
from app.settings import Settings

logger = logging.getLogger("skillgraph")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = app.state.settings
    if settings.run_migrations:
        await run_in_threadpool(run_migrations, settings.database_url)
    if settings.auto_seed:
        await run_in_threadpool(seed_if_empty, app.state.session_factory)
    yield
    app.state.engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    active = settings or Settings()
    engine = make_engine(active.database_url)
    app = FastAPI(title="SkillGraph", version="0.1.0", lifespan=lifespan)
    app.state.settings = active
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)
    app.state.graph_cache = GraphCache()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=active.cors_origin_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)

    @app.exception_handler(DomainError)
    async def _domain_error(_request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail, "code": exc.code})

    return app


app = create_app()


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from netvault.config import Settings
from netvault.dashboard import load_dashboard
from netvault.schemas import Dashboard


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with factory() as session:
        yield session


def create_app(settings: Settings | None = None, engine: AsyncEngine | None = None) -> FastAPI:
    config = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        db = engine if engine is not None else create_async_engine(config.database_url())
        app.state.session_factory = async_sessionmaker(db, expire_on_commit=False)
        app.state.engine = db
        app.state.started = True
        try:
            yield
        finally:
            app.state.started = False
            if engine is None:
                await db.dispose()

    app = FastAPI(title="NetVault", version="0.1.0", lifespan=lifespan)
    if config.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.cors_origins,
            allow_methods=["GET"],
            allow_headers=["Content-Type"],
        )

    @app.get("/healthz")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/startupz")
    async def startup(request: Request) -> dict[str, str]:
        if not getattr(request.app.state, "started", False):
            raise HTTPException(status_code=503, detail="Application has not started")
        return {"status": "ok"}

    @app.get("/readyz")
    async def ready(request: Request) -> dict[str, str]:
        try:
            async with request.app.state.engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Database is not ready") from exc
        return {"status": "ok"}

    @app.get("/api/v1/dashboard", response_model=Dashboard)
    async def dashboard(
        site: str = Query(default="eu-dublin", pattern=r"^[a-z0-9-]{1,80}$"),
        session: AsyncSession = Depends(get_session),
    ) -> Dashboard:
        try:
            return await load_dashboard(session, site)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.get("/{path:path}", include_in_schema=False, response_model=None)
    async def static_file(path: str) -> FileResponse:
        root = config.static_dir.resolve()
        candidate = (root / (path or "index.html")).resolve()
        if candidate != root and root not in candidate.parents:
            raise HTTPException(status_code=404)
        if candidate.is_dir():
            candidate /= "index.html"
        if not candidate.is_file():
            raise HTTPException(status_code=404)
        return FileResponse(candidate)

    return app


app = create_app()

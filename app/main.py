from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app import __version__
from app.api import health
from app.api.v1 import router as api_v1
from app.core.config import get_settings
from app.domain.errors import ConflictError, NotFoundError
from app.repositories.stations import StationRepository
from app.repositories.terminals import TerminalRepository


async def conflict_handler(request: Request, exc: Exception) -> JSONResponse:
    """Repository'nin teklik hatalarını tek yerde 409'a çevirir."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT, content={"detail": str(exc)}
    )


async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)}
    )


def create_app() -> FastAPI:
    settings = get_settings()
    docs_enabled = settings.docs_enabled

    app = FastAPI(
        title="fuelpay-tsm",
        version=__version__,
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )
    app.state.station_repo = StationRepository()
    app.state.terminal_repo = TerminalRepository()
    app.add_exception_handler(ConflictError, conflict_handler)
    app.add_exception_handler(NotFoundError, not_found_handler)
    app.include_router(health.router)
    app.include_router(api_v1.router)
    return app

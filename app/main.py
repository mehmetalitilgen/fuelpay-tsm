from fastapi import FastAPI

from app import __version__
from app.api import health
from app.core.config import get_settings


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
    app.include_router(health.router)
    return app

from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app import __version__
from app.core.config import Environment, Settings, get_settings


class StatusResponse(BaseModel):
    status: Literal["ok"]
    service: Literal["fuelpay-tsm"]
    version: str
    environment: Environment


router = APIRouter(tags=["health"])


@router.get("/health")
async def health(
    settings: Annotated[Settings, Depends(get_settings)],
) -> StatusResponse:
    return StatusResponse(
        status="ok",
        service="fuelpay-tsm",
        version=__version__,
        environment=settings.environment,
    )

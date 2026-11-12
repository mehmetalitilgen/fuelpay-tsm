from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel


class StatusResponse(BaseModel):
    status: Literal["ok"]
    service: Literal["fuelpay-tsm"]
    version: str


router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> StatusResponse:
    status = StatusResponse(status="ok", service="fuelpay-tsm", version="0.1.0")
    return status

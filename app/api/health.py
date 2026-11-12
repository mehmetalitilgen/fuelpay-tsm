from fastapi import APIRouter
from pydantic import BaseModel


class StatusResponse(BaseModel):
    status: str


router = APIRouter(tags=["health"])


@router.get("/health", response_model=StatusResponse)
async def health() -> StatusResponse:
    status = StatusResponse(status="ok")
    return status

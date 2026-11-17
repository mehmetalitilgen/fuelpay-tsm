import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, Response, status

from app.api.deps import StationRepoDep
from app.schemas.errors import error_response
from app.schemas.stations import (
    DEFAULT_PAGE_LIMIT,
    MAX_PAGE_LIMIT,
    StationCreate,
    StationList,
    StationRead,
)

router = APIRouter(prefix="/stations", tags=["stations"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=StationRead,
    responses={409: error_response("Bu kodla bir istasyon zaten var")},
)
async def add_station(
    payload: StationCreate,
    repo: StationRepoDep,
    request: Request,
    response: Response,
) -> StationRead:
    if await repo.get_by_code(payload.code):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Station {payload.code} is already created",
        )

    new_station = await repo.add(payload)

    response.headers["Location"] = str(
        request.url_for("get_station", station_id=new_station.id)
    )
    return new_station


@router.get("", response_model=StationList)
async def list_stations(
    repo: StationRepoDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
) -> StationList:
    return StationList(
        items=await repo.get_list(offset=offset, limit=limit),
        total=await repo.get_sum(),
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{station_id}",
    response_model=StationRead,
    responses={404: error_response("İstasyon bulunamadı")},
)
async def get_station(
    station_id: uuid.UUID,
    repo: StationRepoDep,
) -> StationRead:
    station = await repo.get_by_id(station_id=station_id)
    if station is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station {station_id} not found",
        )
    return station

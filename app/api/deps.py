from typing import Annotated

from fastapi import Depends, Request

from app.repositories.stations import StationRepository


async def get_station_repo(request: Request) -> StationRepository:
    return request.app.state.station_repo


StationRepoDep = Annotated[StationRepository, Depends(get_station_repo)]

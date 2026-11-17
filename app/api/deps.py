from typing import Annotated

from fastapi import Depends, Request

from app.repositories.stations import StationRepository
from app.repositories.terminals import TerminalRepository


async def get_station_repo(request: Request) -> StationRepository:
    return request.app.state.station_repo


async def get_terminal_repo(request: Request) -> TerminalRepository:
    return request.app.state.terminal_repo


StationRepoDep = Annotated[StationRepository, Depends(get_station_repo)]

TerminalRepoDep = Annotated[TerminalRepository, Depends(get_terminal_repo)]

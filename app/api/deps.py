from typing import Annotated

from fastapi import Depends, Request

from app.repositories.stations import StationRepository
from app.repositories.terminals import TerminalRepository
from app.services.terminals import TerminalService


async def get_station_repo(request: Request) -> StationRepository:
    repo: StationRepository = request.app.state.station_repo
    return repo


async def get_terminal_repo(request: Request) -> TerminalRepository:
    repo: TerminalRepository = request.app.state.terminal_repo
    return repo


StationRepoDep = Annotated[StationRepository, Depends(get_station_repo)]

TerminalRepoDep = Annotated[TerminalRepository, Depends(get_terminal_repo)]


async def get_terminal_service(
    station_repo_dep: StationRepoDep, terminal_repo_dep: TerminalRepoDep
) -> TerminalService:
    return TerminalService(stations=station_repo_dep, terminals=terminal_repo_dep)


TerminalServiceDep = Annotated[TerminalService, Depends(get_terminal_service)]

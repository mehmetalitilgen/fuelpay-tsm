import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, Response, status

from app.api.deps import StationRepoDep, TerminalRepoDep
from app.domain.terminal_status import Action
from app.repositories.terminals import TerminalRepository
from app.schemas.errors import error_response
from app.schemas.pagination import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT
from app.schemas.terminals import (
    TerminalCreate,
    TerminalList,
    TerminalRead,
    TerminalSuspend,
)

router = APIRouter(tags=["terminals"])


@router.post(
    "/stations/{station_id}/terminals",
    status_code=status.HTTP_201_CREATED,
    response_model=TerminalRead,
    responses={
        404: error_response("İstasyon bulunamadı"),
        409: error_response(
            "Seri numarası sistemde kayıtlı ya da pompa bu istasyonda dolu"
        ),
    },
)
async def add_terminal(
    station_id: uuid.UUID,
    payload: TerminalCreate,
    terminal_repo: TerminalRepoDep,
    station_repo: StationRepoDep,
    request: Request,
    response: Response,
) -> TerminalRead:

    if await station_repo.get_by_id(station_id=station_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station {station_id} not found",
        )

    terminal = await terminal_repo.add(station_id, payload)

    response.headers["Location"] = str(
        request.url_for("get_terminal", terminal_id=terminal.id)
    )
    return terminal


@router.get(
    "/stations/{station_id}/terminals",
    response_model=TerminalList,
    responses={404: error_response("İstasyon bulunamadı")},
)
async def list_station_terminals(
    station_id: uuid.UUID,
    station_repo: StationRepoDep,
    terminal_repo: TerminalRepoDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
) -> TerminalList:
    if await station_repo.get_by_id(station_id=station_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station {station_id} not found",
        )

    return TerminalList(
        items=await terminal_repo.list_by_station(
            station_id, offset=offset, limit=limit
        ),
        total=await terminal_repo.count_by_station(station_id),
        limit=limit,
        offset=offset,
    )


@router.get(
    "/terminals/{terminal_id}",
    response_model=TerminalRead,
    responses={404: error_response("Terminal bulunamadı")},
)
async def get_terminal(
    terminal_id: uuid.UUID,
    repo: TerminalRepoDep,
) -> TerminalRead:
    terminal = await repo.get_by_id(terminal_id=terminal_id)
    if terminal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Terminal {terminal_id} not found",
        )
    return terminal


STATUS_CHANGE_RESPONSES = {
    404: error_response("Terminal bulunamadı"),
    409: error_response("Bu işlem terminalin mevcut durumunda yapılamaz"),
}


async def _change_status_or_404(
    repo: TerminalRepository,
    terminal_id: uuid.UUID,
    action: Action,
    reason: str | None = None,
) -> TerminalRead:
    terminal = await repo.change_status(terminal_id, action, reason)
    if terminal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Terminal {terminal_id} not found",
        )
    return terminal


@router.post(
    "/terminals/{terminal_id}/activate",
    response_model=TerminalRead,
    responses=STATUS_CHANGE_RESPONSES,
)
async def activate_terminal(
    terminal_id: uuid.UUID,
    repo: TerminalRepoDep,
) -> TerminalRead:
    return await _change_status_or_404(repo, terminal_id, "activate")


@router.post(
    "/terminals/{terminal_id}/suspend",
    response_model=TerminalRead,
    responses=STATUS_CHANGE_RESPONSES,
)
async def suspend_terminal(
    terminal_id: uuid.UUID,
    payload: TerminalSuspend,
    repo: TerminalRepoDep,
) -> TerminalRead:
    return await _change_status_or_404(repo, terminal_id, "suspend", payload.reason)


@router.post(
    "/terminals/{terminal_id}/decommission",
    response_model=TerminalRead,
    responses=STATUS_CHANGE_RESPONSES,
)
async def decommission_terminal(
    terminal_id: uuid.UUID,
    repo: TerminalRepoDep,
) -> TerminalRead:
    return await _change_status_or_404(repo, terminal_id, "decommission")

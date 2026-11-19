import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Query, Request, Response, status

from app.api.deps import TerminalServiceDep
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
    terminal_service: TerminalServiceDep,
    request: Request,
    response: Response,
) -> TerminalRead:
    terminal = await terminal_service.register(station_id, payload)

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
    terminal_service: TerminalServiceDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
) -> TerminalList:
    items, total = await terminal_service.list_for_station(station_id, offset, limit)
    return TerminalList(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/terminals/{terminal_id}",
    response_model=TerminalRead,
    responses={404: error_response("Terminal bulunamadı")},
)
async def get_terminal(
    terminal_id: uuid.UUID,
    terminal_service: TerminalServiceDep,
) -> TerminalRead:

    terminal = await terminal_service.get(terminal_id)
    return terminal


STATUS_CHANGE_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: error_response("Terminal bulunamadı"),
    409: error_response("Bu işlem terminalin mevcut durumunda yapılamaz"),
}


@router.post(
    "/terminals/{terminal_id}/activate",
    response_model=TerminalRead,
    responses=STATUS_CHANGE_RESPONSES,
)
async def activate_terminal(
    terminal_id: uuid.UUID,
    terminal_service: TerminalServiceDep,
) -> TerminalRead:
    return await terminal_service.change_status(terminal_id, "activate")


@router.post(
    "/terminals/{terminal_id}/suspend",
    response_model=TerminalRead,
    responses=STATUS_CHANGE_RESPONSES,
)
async def suspend_terminal(
    terminal_id: uuid.UUID,
    payload: TerminalSuspend,
    terminal_service: TerminalServiceDep,
) -> TerminalRead:
    return await terminal_service.change_status(terminal_id, "suspend", payload.reason)


@router.post(
    "/terminals/{terminal_id}/decommission",
    response_model=TerminalRead,
    responses=STATUS_CHANGE_RESPONSES,
)
async def decommission_terminal(
    terminal_id: uuid.UUID,
    terminal_service: TerminalServiceDep,
) -> TerminalRead:
    return await terminal_service.change_status(terminal_id, "decommission")

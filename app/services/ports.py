import uuid
from typing import Protocol

from app.domain.terminal_status import Action
from app.schemas.pagination import DEFAULT_PAGE_LIMIT
from app.schemas.stations import StationRead
from app.schemas.terminals import TerminalCreate, TerminalRead


class TerminalRepositoryPort(Protocol):
    async def add(
        self, station_id: uuid.UUID, terminal: TerminalCreate
    ) -> TerminalRead: ...

    async def get_by_id(self, terminal_id: uuid.UUID) -> TerminalRead | None: ...

    async def list_by_station(
        self,
        station_id: uuid.UUID,
        offset: int = 0,
        limit: int = DEFAULT_PAGE_LIMIT,
    ) -> list[TerminalRead]: ...

    async def count_by_station(self, station_id: uuid.UUID) -> int: ...

    async def change_status(
        self, terminal_id: uuid.UUID, action: Action, reason: str | None = None
    ) -> TerminalRead | None: ...


class StationRepositoryPort(Protocol):
    """TerminalService'in istasyon deposundan tek ihtiyacı: istasyon var mı."""

    async def get_by_id(self, station_id: uuid.UUID) -> StationRead | None: ...

import uuid

from app.domain.errors import StationNotFoundError, TerminalNotFoundError
from app.domain.terminal_status import Action
from app.schemas.terminals import TerminalCreate, TerminalRead
from app.services.ports import StationRepositoryPort, TerminalRepositoryPort


class TerminalService:
    def __init__(
        self, stations: StationRepositoryPort, terminals: TerminalRepositoryPort
    ):
        self.stations = stations
        self.terminals = terminals

    async def register(
        self, station_id: uuid.UUID, payload: TerminalCreate
    ) -> TerminalRead:
        station = await self.stations.get_by_id(station_id=station_id)
        if station is None:
            raise StationNotFoundError(station_id)

        return await self.terminals.add(station_id, payload)

    async def get(self, terminal_id: uuid.UUID) -> TerminalRead:
        terminal = await self.terminals.get_by_id(terminal_id)
        if terminal is None:
            raise TerminalNotFoundError(terminal_id)

        return terminal

    async def list_for_station(
        self, station_id: uuid.UUID, offset: int, limit: int
    ) -> tuple[list[TerminalRead], int]:
        station = await self.stations.get_by_id(station_id=station_id)
        if station is None:
            raise StationNotFoundError(station_id)

        items = await self.terminals.list_by_station(
            station_id, offset=offset, limit=limit
        )
        total = await self.terminals.count_by_station(station_id)
        return items, total

    async def change_status(
        self, terminal_id: uuid.UUID, action: Action, reason: str | None = None
    ) -> TerminalRead:

        terminal = await self.terminals.change_status(terminal_id, action, reason)
        if terminal is None:
            raise TerminalNotFoundError(terminal_id)

        return terminal

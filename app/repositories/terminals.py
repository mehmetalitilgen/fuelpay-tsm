import uuid
from datetime import UTC, datetime
from itertools import islice

from app.repositories.errors import (
    DuplicatePumpNumberError,
    DuplicateSerialNumberError,
)
from app.schemas.terminals import DEFAULT_PAGE_LIMIT, TerminalCreate, TerminalRead


class TerminalRepository:
    def __init__(self) -> None:
        self.terminals: dict[uuid.UUID, dict] = {}

    async def add(
        self, station_id: uuid.UUID, terminal: TerminalCreate
    ) -> TerminalRead:
        if any(
            existing["serial_number"] == terminal.serial_number
            for existing in self.terminals.values()
        ):
            raise DuplicateSerialNumberError(terminal.serial_number)
        if any(
            existing["station_id"] == station_id
            and existing["pump_number"] == terminal.pump_number
            for existing in self.terminals.values()
        ):
            raise DuplicatePumpNumberError(station_id, terminal.pump_number)

        terminal_id = uuid.uuid4()
        record = {
            "id": terminal_id,
            "station_id": station_id,
            **terminal.model_dump(),
            "status": "registered",
            "created_at": datetime.now(UTC),
        }
        created = TerminalRead(**record)
        self.terminals[terminal_id] = record
        return created

    async def get_by_id(self, terminal_id: uuid.UUID) -> TerminalRead | None:
        terminal = self.terminals.get(terminal_id)
        return TerminalRead(**terminal) if terminal else None

    async def get_sum(self) -> int:
        return len(self.terminals)

    async def list_by_station(
        self,
        station_id: uuid.UUID,
        offset: int = 0,
        limit: int = DEFAULT_PAGE_LIMIT,
    ) -> list[TerminalRead]:
        matching = sorted(
            (
                terminal
                for terminal in self.terminals.values()
                if terminal["station_id"] == station_id
            ),
            key=lambda terminal: terminal["pump_number"],
        )
        return [
            TerminalRead(**terminal)
            for terminal in islice(matching, offset, offset + limit)
        ]

    async def count_by_station(self, station_id: uuid.UUID) -> int:
        return sum(
            1
            for terminal in self.terminals.values()
            if terminal["station_id"] == station_id
        )

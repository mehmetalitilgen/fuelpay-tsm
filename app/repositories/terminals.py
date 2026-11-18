import uuid
from datetime import UTC, datetime
from itertools import islice

from app.domain.errors import (
    DuplicatePumpNumberError,
    DuplicateSerialNumberError,
)
from app.domain.terminal_status import Action, next_status
from app.schemas.pagination import DEFAULT_PAGE_LIMIT
from app.schemas.terminals import TerminalCreate, TerminalRead


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
        # Hizmetten çıkarılan terminal pompayı serbest bırakır; seri numarasını değil.
        if any(
            existing["station_id"] == station_id
            and existing["pump_number"] == terminal.pump_number
            and existing["status"] != "decommissioned"
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
            "status_changed_at": None,
            "suspension_reason": None,
        }
        created = TerminalRead(**record)
        self.terminals[terminal_id] = record
        return created

    async def get_by_id(self, terminal_id: uuid.UUID) -> TerminalRead | None:
        terminal = self.terminals.get(terminal_id)
        return TerminalRead(**terminal) if terminal else None

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

    async def change_status(
        self, terminal_id: uuid.UUID, action: Action, reason: str | None = None
    ) -> TerminalRead | None:
        terminal = self.terminals.get(terminal_id)
        if terminal is None:
            return None

        target = next_status(terminal["status"], action)
        updated = {
            **terminal,
            "status": target,
            "status_changed_at": datetime.now(UTC),
            # Neden yalnızca askıdayken anlamlıdır; diğer geçişlerde temizlenir.
            "suspension_reason": reason if target == "suspended" else None,
        }
        validated = TerminalRead(**updated)
        self.terminals[terminal_id] = updated
        return validated

import uuid
from datetime import UTC, datetime
from itertools import islice
from typing import Any

from app.schemas.pagination import DEFAULT_PAGE_LIMIT
from app.schemas.stations import StationCreate, StationRead


class StationRepository:
    def __init__(self) -> None:
        self.stations: dict[uuid.UUID, Any] = {}

    async def add(self, station: StationCreate) -> StationRead:
        station_id = uuid.uuid4()
        self.stations[station_id] = {
            "id": station_id,
            **station.model_dump(),
            "created_at": datetime.now(UTC),
        }
        return StationRead(**self.stations[station_id])

    async def get_by_id(self, station_id: uuid.UUID) -> StationRead | None:
        station = self.stations.get(station_id)
        return StationRead(**station) if station else None

    async def get_by_code(self, code: str) -> StationRead | None:
        for station in self.stations.values():
            if station["code"] == code:
                return StationRead(**station)
        return None

    async def get_list(
        self, offset: int = 0, limit: int = DEFAULT_PAGE_LIMIT
    ) -> list[StationRead]:
        page = islice(self.stations.values(), offset, offset + limit)
        return [StationRead(**station) for station in page]

    async def get_sum(self) -> int:
        return len(self.stations)

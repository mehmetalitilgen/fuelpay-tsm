"""TerminalService testleri (unit, HTTP'siz).

Servis gerçek in-memory repository'lerle kurulur; FastAPI, TestClient ya da
exception handler yoktur. Servisin sözleşmesi exception'larla ifade edilir:
"bulunamadı" -> NotFoundError alt sınıfı, çakışma ve geçersiz geçiş ->
ConflictError alt sınıfı. HTTP koduna çevirmek main.py'nin işidir.
"""

import uuid

import pytest

from app.domain.errors import (
    ConflictError,
    DuplicatePumpNumberError,
    DuplicateSerialNumberError,
    NotFoundError,
    StationNotFoundError,
    TerminalNotFoundError,
)
from app.domain.terminal_status import InvalidStatusTransitionError
from app.repositories.stations import StationRepository
from app.repositories.terminals import TerminalRepository
from app.schemas.stations import StationCreate
from app.schemas.terminals import TerminalCreate
from app.services.terminals import TerminalService

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def stations():
    return StationRepository()


@pytest.fixture
def terminals():
    return TerminalRepository()


@pytest.fixture
def service(stations, terminals):
    return TerminalService(stations=stations, terminals=terminals)


@pytest.fixture
async def station_a(stations):
    return await stations.add(
        StationCreate(code="34-001", name="Kadıköy", city="İstanbul")
    )


@pytest.fixture
async def station_b(stations):
    return await stations.add(
        StationCreate(code="06-001", name="Çankaya", city="Ankara")
    )


def terminal_in(serial: str = "TRM00001", pump: int = 1) -> TerminalCreate:
    return TerminalCreate(serial_number=serial, pump_number=pump)


# --- register ---


async def test_register_returns_registered_terminal_on_station(service, station_a):
    created = await service.register(station_a.id, terminal_in("TRM00001", 3))

    assert (created.station_id, created.pump_number) == (station_a.id, 3)
    assert created.status == "registered"


async def test_register_on_unknown_station_raises_and_stores_nothing(
    service, terminals
):
    missing = uuid.uuid4()

    with pytest.raises(StationNotFoundError) as exc_info:
        await service.register(missing, terminal_in())

    assert exc_info.value.station_id == missing
    # İstasyon kontrolü repository'ye yazmadan önce yapılmalı.
    assert await terminals.count_by_station(missing) == 0


async def test_register_lets_duplicate_errors_through(service, station_a, station_b):
    await service.register(station_a.id, terminal_in("TRM00001", 1))

    with pytest.raises(DuplicateSerialNumberError):
        await service.register(station_b.id, terminal_in("TRM00001", 1))
    with pytest.raises(DuplicatePumpNumberError):
        await service.register(station_a.id, terminal_in("TRM00002", 1))


# --- get ---


async def test_get_returns_terminal(service, station_a):
    created = await service.register(station_a.id, terminal_in())
    assert await service.get(created.id) == created


async def test_get_unknown_terminal_raises(service):
    missing = uuid.uuid4()

    with pytest.raises(TerminalNotFoundError) as exc_info:
        await service.get(missing)

    assert exc_info.value.terminal_id == missing


# --- list_for_station ---


async def test_list_for_station_returns_page_and_total(service, station_a, station_b):
    for i, pump in enumerate([7, 2, 5]):
        await service.register(station_a.id, terminal_in(f"TRA{i:05d}", pump))
    await service.register(station_b.id, terminal_in("TRB00001", 1))  # karışmamalı

    items, total = await service.list_for_station(station_a.id, offset=0, limit=2)

    assert [t.pump_number for t in items] == [2, 5]  # sayfa, pompa sırasıyla
    assert total == 3  # toplam sayfaya değil istasyona göre


async def test_list_for_station_empty_station(service, station_a):
    assert await service.list_for_station(station_a.id, offset=0, limit=50) == ([], 0)


async def test_list_for_unknown_station_raises(service):
    missing = uuid.uuid4()

    with pytest.raises(StationNotFoundError) as exc_info:
        await service.list_for_station(missing, offset=0, limit=50)

    assert exc_info.value.station_id == missing


# --- change_status ---


async def test_change_status_applies_transition(service, station_a):
    created = await service.register(station_a.id, terminal_in())

    active = await service.change_status(created.id, "activate")
    suspended = await service.change_status(created.id, "suspend", "Arıza")

    assert active.status == "active"
    assert (suspended.status, suspended.suspension_reason) == ("suspended", "Arıza")
    assert (await service.get(created.id)).status == "suspended"


async def test_change_status_unknown_terminal_raises(service):
    missing = uuid.uuid4()

    with pytest.raises(TerminalNotFoundError) as exc_info:
        await service.change_status(missing, "activate")

    assert exc_info.value.terminal_id == missing


async def test_change_status_invalid_transition_raises_and_keeps_status(
    service, station_a
):
    created = await service.register(station_a.id, terminal_in())

    with pytest.raises(InvalidStatusTransitionError):
        await service.change_status(created.id, "suspend", "Arıza")

    assert (await service.get(created.id)).status == "registered"


async def test_decommission_frees_pump_through_service(service, station_a):
    old = await service.register(station_a.id, terminal_in("TRM00001", 4))
    await service.change_status(old.id, "decommission")

    new = await service.register(station_a.id, terminal_in("TRM00002", 4))

    assert new.pump_number == 4


# --- Hata hiyerarşisi: HTTP koduna çeviri bu sınıflara dayanıyor ---


@pytest.mark.parametrize(
    ("error", "base"),
    [
        (StationNotFoundError, NotFoundError),
        (TerminalNotFoundError, NotFoundError),
        (DuplicateSerialNumberError, ConflictError),
        (DuplicatePumpNumberError, ConflictError),
        (InvalidStatusTransitionError, ConflictError),
    ],
)
async def test_service_errors_map_to_http_families(error, base):
    assert issubclass(error, base)

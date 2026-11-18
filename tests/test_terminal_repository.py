"""TerminalRepository davranış sözleşmesi (unit, HTTP'siz).

Epic 4'teki PostgreSQL implementasyonu da bu testlerden geçmeli: yalnızca public
metotlara ve hata tiplerine bakar, iç veri yapısına dokunmaz.
İstasyonun var olup olmadığı repository'nin değil handler'ın işidir.
"""

import uuid
from datetime import UTC, datetime

import pytest

from app.domain.errors import (
    DuplicatePumpNumberError,
    DuplicateSerialNumberError,
)
from app.domain.terminal_status import InvalidStatusTransitionError
from app.repositories.terminals import TerminalRepository
from app.schemas.terminals import TerminalCreate, TerminalRead

pytestmark = pytest.mark.anyio

STATION_A = uuid.UUID("00000000-0000-0000-0000-00000000000a")
STATION_B = uuid.UUID("00000000-0000-0000-0000-00000000000b")


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def repo():
    return TerminalRepository()


def terminal_in(serial: str = "TRM00001", pump: int = 1) -> TerminalCreate:
    return TerminalCreate(serial_number=serial, pump_number=pump)


# --- add ---


async def test_add_returns_registered_terminal(repo):
    before = datetime.now(UTC)
    created = await repo.add(STATION_A, terminal_in("TRM00001", 3))

    assert isinstance(created, TerminalRead)
    assert isinstance(created.id, uuid.UUID)
    assert created.station_id == STATION_A
    assert (created.serial_number, created.pump_number) == ("TRM00001", 3)
    assert created.status == "registered"
    assert created.created_at.tzinfo is not None
    assert before <= created.created_at <= datetime.now(UTC)


async def test_two_terminals_on_same_station_are_both_kept(repo):
    first = await repo.add(STATION_A, terminal_in("TRM00001", 1))
    second = await repo.add(STATION_A, terminal_in("TRM00002", 2))

    assert first.id != second.id
    assert await repo.count_by_station(STATION_A) == 2
    assert await repo.get_by_id(first.id) == first
    assert await repo.get_by_id(second.id) == second


# --- Çakışmalar: kesişimler ---


async def test_duplicate_serial_on_same_station_raises(repo):
    await repo.add(STATION_A, terminal_in("TRM00001", 1))

    with pytest.raises(DuplicateSerialNumberError) as exc_info:
        await repo.add(STATION_A, terminal_in("TRM00001", 2))

    assert exc_info.value.serial_number == "TRM00001"


async def test_duplicate_serial_on_other_station_raises(repo):
    # Seri numarası cihazın kimliği: tüm sistemde tekil.
    await repo.add(STATION_A, terminal_in("TRM00001", 1))

    with pytest.raises(DuplicateSerialNumberError):
        await repo.add(STATION_B, terminal_in("TRM00001", 1))


async def test_duplicate_pump_on_same_station_raises(repo):
    await repo.add(STATION_A, terminal_in("TRM00001", 4))

    with pytest.raises(DuplicatePumpNumberError) as exc_info:
        await repo.add(STATION_A, terminal_in("TRM00002", 4))

    assert exc_info.value.station_id == STATION_A
    assert exc_info.value.pump_number == 4


async def test_same_pump_on_other_station_is_allowed(repo):
    await repo.add(STATION_A, terminal_in("TRM00001", 4))
    other = await repo.add(STATION_B, terminal_in("TRM00002", 4))

    assert (other.station_id, other.pump_number) == (STATION_B, 4)


async def test_failed_add_stores_nothing(repo):
    await repo.add(STATION_A, terminal_in("TRM00001", 1))

    with pytest.raises(DuplicateSerialNumberError):
        await repo.add(STATION_B, terminal_in("TRM00001", 9))
    with pytest.raises(DuplicatePumpNumberError):
        await repo.add(STATION_A, terminal_in("TRM00002", 1))

    assert await repo.count_by_station(STATION_A) == 1
    assert await repo.count_by_station(STATION_B) == 0


# --- get_by_id ---


async def test_get_by_id_returns_none_for_unknown_id(repo):
    await repo.add(STATION_A, terminal_in())
    assert await repo.get_by_id(uuid.uuid4()) is None


async def test_get_by_id_does_not_match_station_id(repo):
    # Kayıtlar terminal id'siyle bulunur; istasyon id'si terminal id'si değildir.
    await repo.add(STATION_A, terminal_in())
    assert await repo.get_by_id(STATION_A) is None


# --- Boş depo ---


async def test_empty_repository(repo):
    assert await repo.list_by_station(STATION_A) == []
    assert await repo.count_by_station(STATION_A) == 0


# --- list_by_station / count_by_station ---


async def test_list_by_station_returns_only_that_station(repo):
    a1 = await repo.add(STATION_A, terminal_in("TRM00001", 1))
    b1 = await repo.add(STATION_B, terminal_in("TRM00002", 1))
    a2 = await repo.add(STATION_A, terminal_in("TRM00003", 2))

    assert await repo.list_by_station(STATION_A) == [a1, a2]
    assert await repo.list_by_station(STATION_B) == [b1]


async def test_list_by_station_orders_by_pump_number(repo):
    # Ekleme sırası (7, 2, 5) beklenen sıradan farklı olmalı; yoksa test sıralamayı
    # yakalayamaz.
    for serial, pump in [("TRM00007", 7), ("TRM00002", 2), ("TRM00005", 5)]:
        await repo.add(STATION_A, terminal_in(serial, pump))
    await repo.add(STATION_B, terminal_in("TRM00001", 1))  # karışmamalı

    pumps = [t.pump_number for t in await repo.list_by_station(STATION_A)]
    assert pumps == [2, 5, 7]


async def test_list_by_station_sorts_before_paginating(repo):
    for i, pump in enumerate([7, 2, 5, 1, 9]):
        await repo.add(STATION_A, terminal_in(f"TRM{i:05d}", pump))

    first = await repo.list_by_station(STATION_A, offset=0, limit=2)
    second = await repo.list_by_station(STATION_A, offset=2, limit=2)
    third = await repo.list_by_station(STATION_A, offset=4, limit=2)

    assert [t.pump_number for t in first] == [1, 2]
    assert [t.pump_number for t in second] == [5, 7]
    assert [t.pump_number for t in third] == [9]


async def test_list_by_station_paginates_within_station(repo):
    created_a = []
    for i in range(5):
        created_a.append(await repo.add(STATION_A, terminal_in(f"TRA{i:05d}", i + 1)))
        await repo.add(STATION_B, terminal_in(f"TRB{i:05d}", i + 1))

    assert await repo.list_by_station(STATION_A, offset=1, limit=2) == created_a[1:3]
    assert await repo.list_by_station(STATION_A, offset=5, limit=2) == []


async def test_list_by_station_default_page_holds_all_32_pumps(repo):
    for i in range(32):
        await repo.add(STATION_A, terminal_in(f"TRA{i:05d}", i + 1))
        await repo.add(STATION_B, terminal_in(f"TRB{i:05d}", i + 1))
    # Tek istasyonda en fazla 32 pompa var; varsayılan limit bunu kesmemeli.
    assert len(await repo.list_by_station(STATION_A)) == 32


async def test_count_by_station(repo):
    for i in range(3):
        await repo.add(STATION_A, terminal_in(f"TRA{i:05d}", i + 1))
    await repo.add(STATION_B, terminal_in("TRB00000", 1))

    assert await repo.count_by_station(STATION_A) == 3
    assert await repo.count_by_station(STATION_B) == 1
    assert await repo.count_by_station(uuid.uuid4()) == 0


async def test_unknown_station_has_empty_list(repo):
    await repo.add(STATION_A, terminal_in())
    assert await repo.list_by_station(uuid.uuid4()) == []


# --- Dönen nesneler depodan bağımsız ---


async def test_mutating_returned_terminal_does_not_change_repository(repo):
    created = await repo.add(STATION_A, terminal_in("TRM00001", 1))

    created.pump_number = 99
    assert (await repo.get_by_id(created.id)).pump_number == 1


async def test_repositories_do_not_share_state():
    first, second = TerminalRepository(), TerminalRepository()
    await first.add(STATION_A, terminal_in())

    assert await second.count_by_station(STATION_A) == 0


# --- change_status ---


async def test_change_status_applies_valid_transition(repo):
    created = await repo.add(STATION_A, terminal_in())
    before = datetime.now(UTC)

    activated = await repo.change_status(created.id, "activate")

    assert activated.status == "active"
    assert before <= activated.status_changed_at <= datetime.now(UTC)
    assert activated.suspension_reason is None
    assert await repo.get_by_id(created.id) == activated


async def test_change_status_rejects_invalid_transition_and_keeps_record(repo):
    created = await repo.add(STATION_A, terminal_in())

    with pytest.raises(InvalidStatusTransitionError):
        await repo.change_status(created.id, "suspend", "Arıza")

    assert await repo.get_by_id(created.id) == created


async def test_change_status_returns_none_for_unknown_terminal(repo):
    assert await repo.change_status(uuid.uuid4(), "activate") is None


async def test_suspension_reason_is_kept_only_while_suspended(repo):
    created = await repo.add(STATION_A, terminal_in())
    await repo.change_status(created.id, "activate")

    suspended = await repo.change_status(created.id, "suspend", "Kart okuyucu arızası")
    assert suspended.suspension_reason == "Kart okuyucu arızası"

    reactivated = await repo.change_status(created.id, "activate")
    assert reactivated.suspension_reason is None


async def test_reason_is_ignored_for_non_suspend_actions(repo):
    created = await repo.add(STATION_A, terminal_in())

    activated = await repo.change_status(created.id, "activate", "gereksiz")

    assert activated.suspension_reason is None


async def test_mutating_returned_status_does_not_change_repository(repo):
    created = await repo.add(STATION_A, terminal_in())
    activated = await repo.change_status(created.id, "activate")

    activated.status = "decommissioned"

    assert (await repo.get_by_id(created.id)).status == "active"


# --- Hizmetten çıkarma: pompa serbest kalır, seri numarası kalmaz ---


async def test_decommissioned_terminal_frees_its_pump(repo):
    old = await repo.add(STATION_A, terminal_in("OLDDEV001", 3))
    await repo.change_status(old.id, "decommission")

    new = await repo.add(STATION_A, terminal_in("NEWDEV001", 3))

    assert new.pump_number == 3
    assert await repo.count_by_station(STATION_A) == 2


@pytest.mark.parametrize("actions", [(), ("activate",), ("activate", "suspend")])
async def test_non_decommissioned_terminal_keeps_its_pump(repo, actions):
    old = await repo.add(STATION_A, terminal_in("OLDDEV001", 3))
    for action in actions:
        await repo.change_status(old.id, action, "Arıza")

    with pytest.raises(DuplicatePumpNumberError):
        await repo.add(STATION_A, terminal_in("NEWDEV001", 3))


async def test_decommissioned_terminal_keeps_its_serial_number(repo):
    old = await repo.add(STATION_A, terminal_in("OLDDEV001", 3))
    await repo.change_status(old.id, "decommission")

    with pytest.raises(DuplicateSerialNumberError):
        await repo.add(STATION_B, terminal_in("OLDDEV001", 1))

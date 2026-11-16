"""StationRepository davranış sözleşmesi (unit, HTTP'siz).

Bu testler Epic 4'te PostgreSQL implementasyonuna da uygulanacak: yalnızca public
metotların davranışına bakar, iç veri yapısına (self.stations) dokunmaz.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.repositories.stations import StationRepository
from app.schemas.stations import StationCreate, StationRead

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def repo():
    return StationRepository()


def station_in(code: str = "34-001", **overrides) -> StationCreate:
    data = {"code": code, "name": "Kadıköy İstasyonu", "city": "İstanbul"}
    return StationCreate(**(data | overrides))


async def add_many(repo: StationRepository, count: int) -> list[StationRead]:
    return [await repo.add(station_in(code=f"34-{i:03d}")) for i in range(count)]


# --- add ---


async def test_add_returns_station_with_input_fields(repo):
    created = await repo.add(station_in(code="35-001", name="Alsancak", city="İzmir"))

    assert isinstance(created, StationRead)
    assert (created.code, created.name, created.city) == ("35-001", "Alsancak", "İzmir")


async def test_add_assigns_uuid_id(repo):
    created = await repo.add(station_in())
    assert isinstance(created.id, uuid.UUID)


async def test_add_assigns_distinct_ids(repo):
    first, second = await add_many(repo, 2)
    assert first.id != second.id


async def test_add_sets_timezone_aware_created_at_now(repo):
    before = datetime.now(UTC)
    created = await repo.add(station_in())
    after = datetime.now(UTC)

    assert created.created_at.tzinfo is not None
    assert created.created_at.utcoffset() == timedelta(0)
    assert before <= created.created_at <= after


# --- get_by_id ---


async def test_get_by_id_returns_added_station(repo):
    created = await repo.add(station_in())
    assert await repo.get_by_id(created.id) == created


async def test_get_by_id_returns_none_for_unknown_id(repo):
    await repo.add(station_in())
    assert await repo.get_by_id(uuid.uuid4()) is None


# --- get_by_code ---


async def test_get_by_code_returns_matching_station(repo):
    await repo.add(station_in(code="34-001"))
    target = await repo.add(station_in(code="06-002"))

    assert await repo.get_by_code("06-002") == target


async def test_get_by_code_returns_none_for_unknown_code(repo):
    await repo.add(station_in(code="34-001"))
    assert await repo.get_by_code("99-999") is None


# --- get_list / get_sum ---


async def test_empty_repository(repo):
    assert await repo.get_list() == []
    assert await repo.get_sum() == 0


async def test_get_list_returns_stations_in_insertion_order(repo):
    created = await add_many(repo, 3)
    assert await repo.get_list() == created


async def test_get_list_default_limit_is_50(repo):
    await add_many(repo, 55)
    assert len(await repo.get_list()) == 50


@pytest.mark.parametrize(
    ("offset", "limit", "expected_indexes"),
    [
        (0, 2, [0, 1]),
        (2, 2, [2, 3]),
        (4, 2, [4]),  # son sayfa eksik dolu
        (5, 2, []),  # offset sonu aşınca boş liste, hata değil
        (0, 10, [0, 1, 2, 3, 4]),
    ],
)
async def test_get_list_paginates(repo, offset, limit, expected_indexes):
    created = await add_many(repo, 5)

    page = await repo.get_list(offset=offset, limit=limit)

    assert page == [created[i] for i in expected_indexes]


async def test_get_sum_counts_all_stations_regardless_of_page(repo):
    await add_many(repo, 5)
    assert await repo.get_sum() == 5


# --- Dönen nesneler depodan bağımsız ---


async def test_mutating_returned_station_does_not_change_repository(repo):
    created = await repo.add(station_in(name="Orijinal"))

    created.name = "Değişti"
    fetched = await repo.get_by_id(created.id)
    fetched.name = "Yine değişti"

    assert (await repo.get_by_id(created.id)).name == "Orijinal"
    assert (await repo.get_list())[0].name == "Orijinal"


async def test_repositories_do_not_share_state():
    first, second = StationRepository(), StationRepository()
    await first.add(station_in())

    assert await second.get_sum() == 0

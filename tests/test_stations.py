"""/api/v1/stations integration testleri.

`client` fixture'ı (tests/conftest.py) her test için yeni bir app, dolayısıyla boş bir
repository kurar. Her test ihtiyacı olan istasyonu kendisi oluşturur.
"""

import uuid
from datetime import datetime

import pytest

from tests.helpers import (
    ERROR_SCHEMA,
    STATIONS_URL,
    create_station,
    documented_error_schema,
    station_payload,
)

STATION_FIELDS = {"id", "code", "name", "city", "created_at"}


# --- POST /api/v1/stations: başarılı oluşturma ---


def test_create_returns_201_with_station(client):
    payload = station_payload()

    response = client.post(STATIONS_URL, json=payload)

    assert response.status_code == 201
    body = response.json()
    assert set(body) == STATION_FIELDS
    assert {k: body[k] for k in payload} == payload


def test_create_returns_valid_uuid_id(client):
    body = create_station(client)
    assert str(uuid.UUID(body["id"])) == body["id"]


def test_create_returns_timezone_aware_created_at(client):
    body = create_station(client)
    created_at = datetime.fromisoformat(body["created_at"])
    assert created_at.tzinfo is not None


def test_create_sets_location_header_to_new_resource(client):
    response = client.post(STATIONS_URL, json=station_payload())
    station_id = response.json()["id"]

    location = response.headers["location"]

    assert location == f"http://testserver{STATIONS_URL}/{station_id}"
    fetched = client.get(location)
    assert fetched.status_code == 200
    assert fetched.json() == response.json()


def test_create_without_trailing_slash_is_not_redirected(client):
    # Terminaller POST'ta redirect takip etmeyebilir; doğrudan 201 dönmeli.
    response = client.post(STATIONS_URL, json=station_payload(), follow_redirects=False)
    assert response.status_code == 201


def test_create_strips_surrounding_whitespace(client):
    # FTSM-003 AC-4'ten bilinçli sapma (Lead onaylı): " 35-004" reddedilmez,
    # kırpılıp tek biçimde saklanır. AC-4 ticket'ta buna göre güncellenecek.
    body = create_station(
        client, code=" 34-001 ", name="  Kadıköy  ", city=" İstanbul "
    )
    assert (body["code"], body["name"], body["city"]) == (
        "34-001",
        "Kadıköy",
        "İstanbul",
    )


def test_create_accepts_max_length_name_and_city(client):
    body = create_station(client, name="n" * 100, city="c" * 50)
    assert (len(body["name"]), len(body["city"])) == (100, 50)


# --- POST: çakışma ---


def test_create_duplicate_code_returns_409(client):
    create_station(client, code="34-001")

    response = client.post(STATIONS_URL, json=station_payload(code="34-001"))

    assert response.status_code == 409
    assert "34-001" in response.json()["detail"]


def test_duplicate_code_is_not_stored(client):
    create_station(client, code="34-001")
    client.post(STATIONS_URL, json=station_payload(code="34-001", name="Başka"))

    listing = client.get(STATIONS_URL).json()

    assert listing["total"] == 1
    assert listing["items"][0]["name"] == "Kadıköy İstasyonu"


# --- POST: doğrulama (422) ---


@pytest.mark.parametrize(
    "code",
    ["35-4", "3-001", "350-01", "35001", "ab-cde", "35-0011", "35_001", ""],
)
def test_create_rejects_invalid_code_format(client, code):
    response = client.post(STATIONS_URL, json=station_payload(code=code))
    assert response.status_code == 422


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", ""),
        ("name", "   "),  # kırpılınca boş
        ("name", "n" * 101),
        ("city", ""),
        ("city", "   "),
        ("city", "c" * 51),
    ],
)
def test_create_rejects_invalid_name_or_city(client, field, value):
    response = client.post(STATIONS_URL, json=station_payload(**{field: value}))
    assert response.status_code == 422


@pytest.mark.parametrize("missing", ["code", "name", "city"])
def test_create_rejects_missing_field(client, missing):
    payload = station_payload()
    del payload[missing]

    response = client.post(STATIONS_URL, json=payload)

    assert response.status_code == 422
    assert ["body", missing] in [err["loc"] for err in response.json()["detail"]]


def test_create_rejects_non_json_body(client):
    response = client.post(STATIONS_URL, content="not json")
    assert response.status_code == 422


def test_create_rejects_unknown_field(client):
    response = client.post(STATIONS_URL, json=station_payload(id=str(uuid.uuid4())))

    assert response.status_code == 422
    assert ["body", "id"] in [err["loc"] for err in response.json()["detail"]]


def test_rejected_create_is_not_stored(client):
    client.post(STATIONS_URL, json=station_payload(code="bad"))
    assert client.get(STATIONS_URL).json()["total"] == 0


# --- GET /api/v1/stations/{id} ---


def test_get_station_returns_created_station(client):
    created = create_station(client)

    response = client.get(f"{STATIONS_URL}/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_unknown_station_returns_404(client):
    missing_id = uuid.uuid4()

    response = client.get(f"{STATIONS_URL}/{missing_id}")

    assert response.status_code == 404
    assert str(missing_id) in response.json()["detail"]


def test_get_station_with_invalid_uuid_returns_422(client):
    response = client.get(f"{STATIONS_URL}/not-a-uuid")
    assert response.status_code == 422


# --- GET /api/v1/stations (liste) ---


def test_list_empty(client):
    response = client.get(STATIONS_URL)

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "limit": 50, "offset": 0}


def test_list_default_page_size_is_50(client):
    # FTSM-003: terminaller sayfa başına 50 kayıt bekliyor.
    created = [create_station(client, code=f"34-{i:03d}") for i in range(51)]

    first_page = client.get(STATIONS_URL).json()
    second_page = client.get(STATIONS_URL, params={"offset": 50}).json()

    assert first_page["items"] == created[:50]
    assert (first_page["total"], first_page["limit"]) == (51, 50)
    assert second_page["items"] == created[50:]


def test_list_returns_created_stations_in_order(client):
    created = [create_station(client, code=f"34-{i:03d}") for i in range(3)]

    body = client.get(STATIONS_URL).json()

    assert body["items"] == created
    assert body["total"] == 3


def test_list_paginates_with_offset_and_limit(client):
    created = [create_station(client, code=f"34-{i:03d}") for i in range(5)]

    body = client.get(STATIONS_URL, params={"offset": 2, "limit": 2}).json()

    assert body["items"] == created[2:4]
    assert (body["total"], body["offset"], body["limit"]) == (5, 2, 2)


def test_list_offset_past_end_returns_empty_page(client):
    create_station(client)

    body = client.get(STATIONS_URL, params={"offset": 10}).json()

    assert body["items"] == []
    assert body["total"] == 1


@pytest.mark.parametrize(
    "params",
    [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"limit": "abc"}],
)
def test_list_rejects_invalid_pagination(client, params):
    response = client.get(STATIONS_URL, params=params)
    assert response.status_code == 422


def test_list_accepts_max_limit(client):
    response = client.get(STATIONS_URL, params={"limit": 100})
    assert response.status_code == 200


# --- Versiyonlama (ADR-0003) ---


def test_stations_are_only_served_under_v1_prefix(client):
    assert client.get("/stations").status_code == 404
    assert client.post("/stations", json=station_payload()).status_code == 404


# --- OpenAPI: hata yanıtları belgelenmiş mi ---


@pytest.mark.parametrize(
    ("method", "path", "code"),
    [
        ("post", "/api/v1/stations", 409),
        ("get", "/api/v1/stations/{station_id}", 404),
    ],
)
def test_openapi_documents_station_errors(openapi, method, path, code):
    assert documented_error_schema(openapi, method, path, code) == ERROR_SCHEMA


def test_openapi_error_schema_is_detail_string(openapi):
    schema = openapi["components"]["schemas"]["ErrorResponse"]
    assert schema["required"] == ["detail"]
    assert schema["properties"]["detail"]["type"] == "string"


def test_station_error_bodies_match_documented_schema(client):
    create_station(client, code="34-001")
    conflict = client.post(STATIONS_URL, json=station_payload(code="34-001"))
    missing = client.get(f"{STATIONS_URL}/{uuid.uuid4()}")

    for response in (conflict, missing):
        assert set(response.json()) == {"detail"}
        assert isinstance(response.json()["detail"], str)

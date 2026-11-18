"""Terminal endpoint'leri integration testleri.

Hatalar kesişimlerde çıkar: senaryoların çoğu iki istasyon kurar. Her test kendi
istasyon ve terminallerini oluşturur; `client` her test için boş bir app kurar.
"""

import uuid
from datetime import datetime

import pytest

from tests.helpers import (
    ERROR_SCHEMA,
    TERMINALS_URL,
    create_station,
    create_terminal,
    documented_error_schema,
    station_terminals_url,
    terminal_payload,
)

TERMINAL_FIELDS = {
    "id",
    "station_id",
    "serial_number",
    "pump_number",
    "status",
    "created_at",
    "status_changed_at",
    "suspension_reason",
}


@pytest.fixture
def station(client):
    return create_station(client, code="34-001")


@pytest.fixture
def other_station(client):
    return create_station(client, code="06-001", name="Çankaya", city="Ankara")


def post_terminal(client, to_station, /, **overrides):
    # to_station positional-only: gövdedeki "station_id" alanıyla çakışmasın.
    return client.post(
        station_terminals_url(to_station), json=terminal_payload(**overrides)
    )


def list_total(client, station_id) -> int:
    return client.get(station_terminals_url(station_id)).json()["total"]


# --- POST /api/v1/stations/{station_id}/terminals: başarılı oluşturma ---


def test_create_returns_201_with_registered_terminal(client, station):
    response = post_terminal(client, station["id"], serial_number="TRM00001")

    assert response.status_code == 201
    body = response.json()
    assert set(body) == TERMINAL_FIELDS
    assert body["station_id"] == station["id"]
    assert (body["serial_number"], body["pump_number"]) == ("TRM00001", 1)
    assert body["status"] == "registered"
    assert str(uuid.UUID(body["id"])) == body["id"]
    assert datetime.fromisoformat(body["created_at"]).tzinfo is not None
    # Yeni terminal hiç durum değiştirmedi ve askıya alınmadı.
    assert body["status_changed_at"] is None
    assert body["suspension_reason"] is None


def test_create_sets_location_header_to_new_terminal(client, station):
    response = post_terminal(client, station["id"])
    terminal_id = response.json()["id"]

    location = response.headers["location"]

    assert location.endswith(f"{TERMINALS_URL}/{terminal_id}")
    fetched = client.get(location)
    assert fetched.status_code == 200
    assert fetched.json() == response.json()


def test_create_without_trailing_slash_is_not_redirected(client, station):
    response = client.post(
        station_terminals_url(station["id"]),
        json=terminal_payload(),
        follow_redirects=False,
    )
    assert response.status_code == 201


@pytest.mark.parametrize(
    ("sent", "stored"),
    [("trm00001", "TRM00001"), ("  TRM00001  ", "TRM00001"), ("Trm00001", "TRM00001")],
)
def test_create_normalizes_serial_number(client, station, sent, stored):
    body = create_terminal(client, station["id"], serial_number=sent)
    assert body["serial_number"] == stored


@pytest.mark.parametrize("pump", [1, 32])
def test_create_accepts_pump_number_bounds(client, station, pump):
    body = create_terminal(client, station["id"], pump_number=pump)
    assert body["pump_number"] == pump


def test_create_accepts_serial_number_length_bounds(client, station):
    create_terminal(client, station["id"], serial_number="A" * 8, pump_number=1)
    create_terminal(client, station["id"], serial_number="B" * 16, pump_number=2)


# --- POST: olmayan istasyon ---


def test_create_on_unknown_station_returns_404(client):
    missing = uuid.uuid4()

    response = post_terminal(client, missing)

    assert response.status_code == 404
    assert str(missing) in response.json()["detail"]


def test_create_on_invalid_station_id_returns_422(client):
    response = post_terminal(client, "not-a-uuid")
    assert response.status_code == 422


def test_create_on_unknown_station_stores_nothing(client, station):
    post_terminal(client, uuid.uuid4(), serial_number="TRM00001")
    # Aynı seri numarası gerçek istasyonda hâlâ kullanılabilir olmalı.
    create_terminal(client, station["id"], serial_number="TRM00001")


# --- POST: çakışmalar (kesişimler) ---


def test_duplicate_serial_on_same_station_returns_409(client, station):
    create_terminal(client, station["id"], serial_number="TRM00001", pump_number=1)

    response = post_terminal(
        client, station["id"], serial_number="TRM00001", pump_number=2
    )

    assert response.status_code == 409
    assert "TRM00001" in response.json()["detail"]


def test_duplicate_serial_on_other_station_returns_409(client, station, other_station):
    create_terminal(client, station["id"], serial_number="TRM00001")

    response = post_terminal(client, other_station["id"], serial_number="TRM00001")

    assert response.status_code == 409


def test_duplicate_serial_with_different_case_returns_409(
    client, station, other_station
):
    create_terminal(client, station["id"], serial_number="TRM0000A", pump_number=1)

    response = post_terminal(
        client, other_station["id"], serial_number=" trm0000a ", pump_number=1
    )

    assert response.status_code == 409


def test_duplicate_pump_on_same_station_returns_409(client, station):
    create_terminal(client, station["id"], serial_number="TRM00001", pump_number=5)

    response = post_terminal(
        client, station["id"], serial_number="TRM00002", pump_number=5
    )

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert "5" in detail
    assert station["id"] in detail


def test_same_pump_on_other_station_is_allowed(client, station, other_station):
    create_terminal(client, station["id"], serial_number="TRM00001", pump_number=5)

    body = create_terminal(
        client, other_station["id"], serial_number="TRM00002", pump_number=5
    )

    assert (body["station_id"], body["pump_number"]) == (other_station["id"], 5)


def test_conflicting_create_stores_nothing(client, station, other_station):
    create_terminal(client, station["id"], serial_number="TRM00001", pump_number=1)
    post_terminal(client, other_station["id"], serial_number="TRM00001")
    post_terminal(client, station["id"], serial_number="TRM00002", pump_number=1)

    assert list_total(client, station["id"]) == 1
    assert list_total(client, other_station["id"]) == 0


# --- POST: doğrulama (422) ---


@pytest.mark.parametrize(
    "serial",
    [
        "TRM0001",  # 7 karakter
        "T" * 17,
        "TRM 0001",  # iç boşluk
        "TRM-0001",
        "TRM_0001",
        "İSTANBUL1",  # İ ASCII değil
        "TRMı0001",  # ı, upper() ile I'ya dönüşmemeli
        "STRAßE12",  # ß, upper() ile SS'e dönüşüp uzunluğu değiştirmemeli
        "TRM٠٠٠١",  # Arap-Hint rakamları
        "",
        "        ",
    ],
)
def test_create_rejects_invalid_serial_number(client, station, serial):
    response = post_terminal(client, station["id"], serial_number=serial)
    assert response.status_code == 422


@pytest.mark.parametrize(
    "pump",
    [
        0,
        33,
        -1,
        3.5,
        3.0,  # tam sayı değerli float da tam sayı değildir
        "3",  # sayı string'i
        " 4 ",  # boşluklu sayı string'i
        True,
        False,
        None,
        "üç",
    ],
)
def test_create_rejects_invalid_pump_number(client, station, pump):
    response = post_terminal(client, station["id"], pump_number=pump)
    assert response.status_code == 422


@pytest.mark.parametrize("missing", ["serial_number", "pump_number"])
def test_create_rejects_missing_field(client, station, missing):
    payload = terminal_payload()
    del payload[missing]

    response = client.post(station_terminals_url(station["id"]), json=payload)

    assert response.status_code == 422
    assert ["body", missing] in [err["loc"] for err in response.json()["detail"]]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", "00000000-0000-0000-0000-000000000001"),
        ("station_id", "00000000-0000-0000-0000-000000000002"),
        ("status", "active"),
        ("created_at", "2020-01-01T00:00:00Z"),
    ],
)
def test_create_rejects_server_owned_fields(client, station, field, value):
    response = post_terminal(client, station["id"], **{field: value})

    assert response.status_code == 422
    assert ["body", field] in [err["loc"] for err in response.json()["detail"]]


def test_rejected_create_stores_nothing(client, station):
    post_terminal(client, station["id"], serial_number="bad")
    assert list_total(client, station["id"]) == 0


# --- GET /api/v1/terminals/{terminal_id} ---


def test_get_terminal_returns_created_terminal(client, station):
    created = create_terminal(client, station["id"])

    response = client.get(f"{TERMINALS_URL}/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_terminal_among_several_stations(client, station, other_station):
    create_terminal(client, station["id"], serial_number="TRM00001")
    target = create_terminal(client, other_station["id"], serial_number="TRM00002")

    response = client.get(f"{TERMINALS_URL}/{target['id']}")

    assert response.json() == target


def test_get_unknown_terminal_returns_404(client):
    missing = uuid.uuid4()

    response = client.get(f"{TERMINALS_URL}/{missing}")

    assert response.status_code == 404
    assert str(missing) in response.json()["detail"]


def test_get_terminal_by_station_id_returns_404(client, station):
    create_terminal(client, station["id"])
    response = client.get(f"{TERMINALS_URL}/{station['id']}")
    assert response.status_code == 404


def test_get_terminal_with_invalid_uuid_returns_422(client):
    response = client.get(f"{TERMINALS_URL}/not-a-uuid")
    assert response.status_code == 422


# --- GET /api/v1/stations/{station_id}/terminals (istasyon bazlı liste) ---


def test_list_empty_station(client, station):
    response = client.get(station_terminals_url(station["id"]))

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "limit": 50, "offset": 0}


def test_list_unknown_station_returns_404(client):
    missing = uuid.uuid4()

    response = client.get(station_terminals_url(missing))

    assert response.status_code == 404
    assert str(missing) in response.json()["detail"]


def test_list_invalid_station_id_returns_422(client):
    response = client.get(station_terminals_url("not-a-uuid"))
    assert response.status_code == 422


def test_list_returns_only_that_stations_terminals(client, station, other_station):
    a1 = create_terminal(client, station["id"], serial_number="TRM00001")
    b1 = create_terminal(client, other_station["id"], serial_number="TRM00002")
    a2 = create_terminal(client, station["id"], serial_number="TRM00003", pump_number=2)

    a_body = client.get(station_terminals_url(station["id"])).json()
    b_body = client.get(station_terminals_url(other_station["id"])).json()

    assert (a_body["items"], a_body["total"]) == ([a1, a2], 2)
    assert (b_body["items"], b_body["total"]) == ([b1], 1)


def test_list_orders_by_pump_number(client, station):
    # Ekleme sırası (7, 2, 5) beklenen sıradan farklı; sıralamayı ancak böyle yakalar.
    for serial, pump in [("TRM00007", 7), ("TRM00002", 2), ("TRM00005", 5)]:
        create_terminal(client, station["id"], serial_number=serial, pump_number=pump)

    body = client.get(station_terminals_url(station["id"])).json()

    assert [t["pump_number"] for t in body["items"]] == [2, 5, 7]


def test_list_pages_follow_pump_order(client, station):
    for i, pump in enumerate([7, 2, 5, 1, 9]):
        create_terminal(
            client, station["id"], serial_number=f"TRM{i:05d}", pump_number=pump
        )

    url = station_terminals_url(station["id"])
    pages = [
        client.get(url, params={"offset": offset, "limit": 2}).json()["items"]
        for offset in (0, 2, 4)
    ]

    assert [[t["pump_number"] for t in page] for page in pages] == [[1, 2], [5, 7], [9]]


def test_list_paginates_within_station(client, station, other_station):
    # Araya başka istasyonun terminalleri girse de sayfalama yalnızca bu istasyonda.
    created = []
    for i in range(5):
        created.append(
            create_terminal(
                client, station["id"], serial_number=f"TRA{i:05d}", pump_number=i + 1
            )
        )
        create_terminal(
            client, other_station["id"], serial_number=f"TRB{i:05d}", pump_number=i + 1
        )

    body = client.get(
        station_terminals_url(station["id"]), params={"offset": 1, "limit": 2}
    ).json()

    assert body["items"] == created[1:3]
    assert (body["total"], body["offset"], body["limit"]) == (5, 1, 2)


def test_list_accepts_min_limit(client, station):
    response = client.get(station_terminals_url(station["id"]), params={"limit": 1})

    assert response.status_code == 200
    assert response.json()["limit"] == 1


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}])
def test_list_rejects_invalid_pagination(client, station, params):
    response = client.get(station_terminals_url(station["id"]), params=params)
    assert response.status_code == 422


def test_there_is_no_global_terminal_list(client, station):
    create_terminal(client, station["id"])
    assert client.get(TERMINALS_URL).status_code in (404, 405)


# --- Versiyonlama (ADR-0003) ---


def test_terminals_are_only_served_under_v1_prefix(client, station):
    assert client.get("/terminals").status_code == 404
    assert (
        client.post(
            f"/stations/{station['id']}/terminals", json=terminal_payload()
        ).status_code
        == 404
    )


def test_api_root_is_not_a_terminal_list(client):
    assert client.get("/api/v1/").status_code == 404


# --- OpenAPI: hata yanıtları belgelenmiş mi ---


@pytest.mark.parametrize(
    ("method", "path", "code"),
    [
        ("post", "/api/v1/stations/{station_id}/terminals", 404),
        ("post", "/api/v1/stations/{station_id}/terminals", 409),
        ("get", "/api/v1/stations/{station_id}/terminals", 404),
        ("get", "/api/v1/terminals/{terminal_id}", 404),
    ],
)
def test_openapi_documents_terminal_errors(openapi, method, path, code):
    assert documented_error_schema(openapi, method, path, code) == ERROR_SCHEMA


def test_terminal_error_bodies_match_documented_schema(client, station):
    # Belgelenen şema ile gerçek gövde ayrışmasın: 409 artık exception handler'dan,
    # 404 HTTPException'dan geliyor; ikisi de aynı biçimde olmalı.
    create_terminal(client, station["id"], serial_number="TRM00001", pump_number=1)
    serial_conflict = post_terminal(
        client, station["id"], serial_number="TRM00001", pump_number=2
    )
    pump_conflict = post_terminal(
        client, station["id"], serial_number="TRM00002", pump_number=1
    )
    missing_station = post_terminal(client, uuid.uuid4())
    missing_terminal = client.get(f"{TERMINALS_URL}/{uuid.uuid4()}")

    assert [
        r.status_code
        for r in (serial_conflict, pump_conflict, missing_station, missing_terminal)
    ] == [409, 409, 404, 404]
    for response in (serial_conflict, pump_conflict, missing_station, missing_terminal):
        assert set(response.json()) == {"detail"}
        assert isinstance(response.json()["detail"], str)


# --- Durum geçişleri (FTSM-005) ---

STATUS_ACTIONS = ("activate", "suspend", "decommission")
# Bir terminali API üzerinden istenen duruma getiren işlem dizileri.
PATH_TO_STATUS = {
    "registered": (),
    "active": ("activate",),
    "suspended": ("activate", "suspend"),
    "decommissioned": ("decommission",),
}


def status_url(terminal_id, action: str) -> str:
    return f"{TERMINALS_URL}/{terminal_id}/{action}"


def apply(client, terminal_id, action: str, reason: str = "Kart okuyucu arızası"):
    body = {"reason": reason} if action == "suspend" else None
    return client.post(status_url(terminal_id, action), json=body)


def terminal_in_status(client, station_id, wanted: str, **overrides) -> dict:
    terminal = create_terminal(client, station_id, **overrides)
    for action in PATH_TO_STATUS[wanted]:
        response = apply(client, terminal["id"], action)
        assert response.status_code == 200, response.text
        terminal = response.json()
    return terminal


def test_new_terminal_has_no_status_history(client, station):
    terminal = create_terminal(client, station["id"])

    assert terminal["status"] == "registered"
    assert terminal["status_changed_at"] is None
    assert terminal["suspension_reason"] is None


def test_full_lifecycle(client, station):
    terminal = create_terminal(client, station["id"], serial_number="FP2A7K91X3")
    url = f"{TERMINALS_URL}/{terminal['id']}"
    steps = [
        ("activate", "active", None),
        ("suspend", "suspended", "Kart okuyucu arızası"),
        ("activate", "active", None),
        ("decommission", "decommissioned", None),
    ]

    previous_change = None
    for action, expected_status, expected_reason in steps:
        response = apply(client, terminal["id"], action)

        assert response.status_code == 200, (action, response.text)
        body = response.json()
        assert (body["status"], body["suspension_reason"]) == (
            expected_status,
            expected_reason,
        )
        changed_at = datetime.fromisoformat(body["status_changed_at"])
        assert changed_at.tzinfo is not None
        if previous_change is not None:
            assert changed_at >= previous_change
        previous_change = changed_at
        assert client.get(url).json() == body


# Beklenen sonuçlar elle yazılı (ADR-0004); geçiş tablosundan türetilmez.
EXPECTED_STATUS_CODES = {
    ("registered", "activate"): 200,
    ("registered", "suspend"): 409,
    ("registered", "decommission"): 200,
    ("active", "activate"): 409,
    ("active", "suspend"): 200,
    ("active", "decommission"): 200,
    ("suspended", "activate"): 200,
    ("suspended", "suspend"): 409,
    ("suspended", "decommission"): 200,
    ("decommissioned", "activate"): 409,
    ("decommissioned", "suspend"): 409,
    ("decommissioned", "decommission"): 409,
}


@pytest.mark.parametrize(("current", "action"), sorted(EXPECTED_STATUS_CODES))
def test_status_transition_matrix(client, station, current, action):
    terminal = terminal_in_status(client, station["id"], current)

    response = apply(client, terminal["id"], action)

    assert response.status_code == EXPECTED_STATUS_CODES[(current, action)]
    if response.status_code == 409:
        assert action in response.json()["detail"]
        unchanged = client.get(f"{TERMINALS_URL}/{terminal['id']}").json()
        assert unchanged == terminal


def test_suspend_strips_reason(client, station):
    terminal = terminal_in_status(client, station["id"], "active")

    response = apply(client, terminal["id"], "suspend", reason="  Kart okuyucu  ")

    assert response.json()["suspension_reason"] == "Kart okuyucu"


def test_suspend_accepts_200_character_reason(client, station):
    terminal = terminal_in_status(client, station["id"], "active")

    response = apply(client, terminal["id"], "suspend", reason="r" * 200)

    assert response.status_code == 200


@pytest.mark.parametrize(
    "body",
    [
        None,
        {},
        {"reason": ""},
        {"reason": "   "},
        {"reason": "r" * 201},
        {"reason": 5},
        {"reason": "Arıza", "status": "active"},
    ],
)
def test_suspend_rejects_invalid_body(client, station, body):
    terminal = terminal_in_status(client, station["id"], "active")

    response = client.post(status_url(terminal["id"], "suspend"), json=body)

    assert response.status_code == 422
    assert client.get(f"{TERMINALS_URL}/{terminal['id']}").json() == terminal


@pytest.mark.parametrize("action", STATUS_ACTIONS)
def test_status_change_on_unknown_terminal_returns_404(client, action):
    response = apply(client, uuid.uuid4(), action)
    assert response.status_code == 404


@pytest.mark.parametrize("action", STATUS_ACTIONS)
def test_status_change_with_invalid_uuid_returns_422(client, action):
    response = apply(client, "not-a-uuid", action)
    assert response.status_code == 422


def test_body_is_validated_before_terminal_lookup(client):
    response = client.post(status_url(uuid.uuid4(), "suspend"), json={"reason": ""})
    assert response.status_code == 422


def test_decommissioned_terminal_frees_its_pump(client, station):
    terminal_in_status(
        client,
        station["id"],
        "decommissioned",
        serial_number="OLDDEV001",
        pump_number=3,
    )

    response = post_terminal(
        client, station["id"], serial_number="NEWDEV001", pump_number=3
    )

    assert response.status_code == 201
    pumps = [
        (t["pump_number"], t["status"])
        for t in client.get(station_terminals_url(station["id"])).json()["items"]
    ]
    assert sorted(pumps) == [(3, "decommissioned"), (3, "registered")]


def test_suspended_terminal_keeps_its_pump(client, station):
    terminal_in_status(
        client, station["id"], "suspended", serial_number="OLDDEV001", pump_number=3
    )

    response = post_terminal(
        client, station["id"], serial_number="NEWDEV001", pump_number=3
    )

    assert response.status_code == 409


def test_decommissioned_serial_number_cannot_be_reused(client, station, other_station):
    terminal_in_status(
        client,
        station["id"],
        "decommissioned",
        serial_number="OLDDEV001",
        pump_number=3,
    )

    response = post_terminal(
        client, other_station["id"], serial_number="olddev001", pump_number=1
    )

    assert response.status_code == 409


def test_list_shows_current_status(client, station):
    terminal_in_status(
        client, station["id"], "suspended", serial_number="TRM00001", pump_number=1
    )
    terminal_in_status(
        client, station["id"], "active", serial_number="TRM00002", pump_number=2
    )

    items = client.get(station_terminals_url(station["id"])).json()["items"]

    assert [(t["pump_number"], t["status"]) for t in items] == [
        (1, "suspended"),
        (2, "active"),
    ]


@pytest.mark.parametrize("action", STATUS_ACTIONS)
@pytest.mark.parametrize("code", [404, 409])
def test_openapi_documents_status_change_errors(openapi, action, code):
    path = f"/api/v1/terminals/{{terminal_id}}/{action}"
    assert documented_error_schema(openapi, "post", path, code) == ERROR_SCHEMA


@pytest.mark.parametrize("action", STATUS_ACTIONS)
def test_openapi_status_change_returns_terminal(openapi, action):
    path = f"/api/v1/terminals/{{terminal_id}}/{action}"
    operation = openapi["paths"][path]["post"]

    assert operation["tags"] == ["terminals"]
    schema = operation["responses"]["200"]["content"]["application/json"]["schema"]
    assert schema == {"$ref": "#/components/schemas/TerminalRead"}


def test_openapi_status_enum_lists_all_states(openapi):
    schemas = openapi["components"]["schemas"]
    status_schema = schemas["TerminalRead"]["properties"]["status"]
    if "$ref" in status_schema:
        status_schema = schemas[status_schema["$ref"].rsplit("/", 1)[-1]]
    assert status_schema["enum"] == [
        "registered",
        "active",
        "suspended",
        "decommissioned",
    ]


def test_openapi_only_suspend_takes_a_body(openapi):
    paths = openapi["paths"]
    has_body = {
        action: "requestBody"
        in paths[f"/api/v1/terminals/{{terminal_id}}/{action}"]["post"]
        for action in STATUS_ACTIONS
    }
    assert has_body == {"activate": False, "suspend": True, "decommission": False}

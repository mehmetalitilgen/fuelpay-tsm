"""Test dosyalarının paylaştığı HTTP yardımcıları.

Her yardımcı geçerli bir gövde üretir; testler yalnızca ilgilendikleri alanı ezer.
"""

STATIONS_URL = "/api/v1/stations"
TERMINALS_URL = "/api/v1/terminals"
ERROR_SCHEMA = {"$ref": "#/components/schemas/ErrorResponse"}


def documented_error_schema(openapi: dict, method: str, path: str, code: int):
    """OpenAPI'de bir endpoint'in verilen hata kodu için belgelediği gövde şeması."""
    responses = openapi["paths"][path][method]["responses"]
    return responses[str(code)]["content"]["application/json"]["schema"]


def station_payload(**overrides) -> dict:
    return {
        "code": "34-001",
        "name": "Kadıköy İstasyonu",
        "city": "İstanbul",
    } | overrides


def create_station(client, **overrides) -> dict:
    response = client.post(STATIONS_URL, json=station_payload(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


def station_terminals_url(station_id: str) -> str:
    return f"{STATIONS_URL}/{station_id}/terminals"


def terminal_payload(**overrides) -> dict:
    return {"serial_number": "TRM00001", "pump_number": 1} | overrides


def create_terminal(client, station_id: str, **overrides) -> dict:
    response = client.post(
        station_terminals_url(station_id), json=terminal_payload(**overrides)
    )
    assert response.status_code == 201, response.text
    return response.json()

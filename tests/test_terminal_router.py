"""Terminal durum endpoint'lerinin router testleri (sahte servisle).

Router'ın işi HTTP'yi servise doğru çevirmek: doğru eylem adı, kırpılmış neden,
servisin sonucunu olduğu gibi döndürmek ve servisin hatasını doğru koda
çevirmek. Bunu kanıtlamak için gerçek servise ve repository'ye gerek yok.
"""

import uuid
from datetime import UTC, datetime

import pytest

from app.api.deps import get_terminal_service
from app.domain.errors import TerminalNotFoundError
from app.schemas.terminals import TerminalRead

TERMINAL_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
STATION_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")

# Sahte servisin döndüğü sabit sonuç; bütün alanlar elle kurulur.
FIXED_TERMINAL = TerminalRead(
    id=TERMINAL_ID,
    station_id=STATION_ID,
    serial_number="TRM00001",
    pump_number=4,
    status="suspended",
    created_at=datetime(2026, 11, 1, 9, 0, tzinfo=UTC),
    status_changed_at=datetime(2026, 11, 19, 10, 30, tzinfo=UTC),
    suspension_reason="Arıza",
)


# --- C1: sahte servis ---


class FakeTerminalService:
    """Çağrıları kaydeder; önceden belirlenen sonucu döner ya da hatayı fırlatır."""

    def __init__(
        self, result: TerminalRead = FIXED_TERMINAL, error: Exception | None = None
    ) -> None:
        self.result = result
        self.error = error
        self.calls: list[tuple[uuid.UUID, str, str | None]] = []

    async def change_status(
        self, terminal_id: uuid.UUID, action: str, reason: str | None = None
    ) -> TerminalRead:
        self.calls.append((terminal_id, action, reason))
        if self.error is not None:
            raise self.error
        return self.result


# --- C2: override fixture'ı ---


@pytest.fixture
def fake_service(client):
    fake = FakeTerminalService()
    client.app.dependency_overrides[get_terminal_service] = lambda: fake
    yield fake
    client.app.dependency_overrides.clear()


def status_url(action: str, terminal_id: uuid.UUID = TERMINAL_ID) -> str:
    return f"/api/v1/terminals/{terminal_id}/{action}"


# --- C3: router testleri ---


def test_suspend_passes_trimmed_reason_and_returns_service_result(client, fake_service):
    response = client.post(status_url("suspend"), json={"reason": " Arıza "})

    assert fake_service.calls == [(TERMINAL_ID, "suspend", "Arıza")]
    assert response.status_code == 200
    assert response.json() == FIXED_TERMINAL.model_dump(mode="json")


@pytest.mark.parametrize("action", ["activate", "decommission"])
def test_bodyless_actions_call_service_with_action_and_no_reason(
    client, fake_service, action
):
    response = client.post(status_url(action))

    assert fake_service.calls == [(TERMINAL_ID, action, None)]
    assert response.status_code == 200
    assert response.json() == FIXED_TERMINAL.model_dump(mode="json")


def test_service_not_found_error_becomes_404(client, fake_service):
    missing = uuid.UUID("33333333-3333-3333-3333-333333333333")
    fake_service.error = TerminalNotFoundError(missing)

    response = client.post(status_url("activate", missing))

    assert response.status_code == 404
    assert response.json() == {"detail": f"Terminal {missing} not found"}
    assert fake_service.calls == [(missing, "activate", None)]

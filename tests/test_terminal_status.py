"""Terminal durum geçiş kuralları (unit, HTTP'siz, repository'siz).

Beklenen tablo burada elle yazılır, TRANSITIONS'tan türetilmez: türetilseydi test
tabloyu kendisiyle karşılaştırırdı ve yanlış bir kuralı yakalayamazdı.
"""

from itertools import product
from typing import get_args

import pytest

from app.domain.terminal_status import (
    TRANSITIONS,
    Action,
    InvalidStatusTransitionError,
    Status,
    next_status,
)
from app.repositories.errors import ConflictError

# (mevcut durum, eylem) -> yeni durum
VALID = {
    ("registered", "activate"): "active",
    ("suspended", "activate"): "active",
    ("active", "suspend"): "suspended",
    ("registered", "decommission"): "decommissioned",
    ("active", "decommission"): "decommissioned",
    ("suspended", "decommission"): "decommissioned",
}

INVALID = {
    ("registered", "suspend"),  # hiç aktif olmamış terminal askıya alınamaz
    ("active", "activate"),  # aynı duruma tekrar geçiş: idempotent değil, 409
    ("suspended", "suspend"),  # aynı duruma tekrar geçiş: idempotent değil, 409
    ("decommissioned", "activate"),  # decommissioned son durumdur
    ("decommissioned", "suspend"),
    ("decommissioned", "decommission"),
}


def test_every_status_action_pair_is_covered():
    # Status ya da Action'a yeni bir değer eklenirse bu test, o kombinasyonların
    # kararı VALID/INVALID'e yazılana kadar kırmızı kalır.
    all_pairs = set(product(get_args(Status), get_args(Action)))

    assert set(VALID) | INVALID == all_pairs
    assert not set(VALID) & INVALID


@pytest.mark.parametrize(("current", "action"), sorted(VALID))
def test_valid_transition_returns_target_status(current, action):
    assert next_status(current, action) == VALID[(current, action)]


@pytest.mark.parametrize(("current", "action"), sorted(INVALID))
def test_invalid_transition_raises(current, action):
    with pytest.raises(InvalidStatusTransitionError) as exc_info:
        next_status(current, action)

    assert (exc_info.value.current, exc_info.value.action) == (current, action)


def test_decommissioned_is_final():
    for action in get_args(Action):
        with pytest.raises(InvalidStatusTransitionError):
            next_status("decommissioned", action)


def test_error_is_a_conflict_so_api_returns_409():
    # main.py'deki ConflictError handler'ı bu hatayı 409'a çevirir.
    assert issubclass(InvalidStatusTransitionError, ConflictError)


def test_error_message_names_action_and_status():
    with pytest.raises(InvalidStatusTransitionError) as exc_info:
        next_status("active", "activate")

    assert str(exc_info.value) == "Cannot 'activate' a terminal in status 'active'."


def test_custom_error_message_is_kept():
    error = InvalidStatusTransitionError("active", "activate", message="özel mesaj")

    assert str(error) == "özel mesaj"
    assert (error.current, error.action) == ("active", "activate")


def test_transitions_table_is_read_only():
    with pytest.raises(TypeError):
        TRANSITIONS["activate"] = (frozenset({"decommissioned"}), "active")

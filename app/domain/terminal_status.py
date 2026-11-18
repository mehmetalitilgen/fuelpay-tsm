from collections.abc import Mapping
from types import MappingProxyType
from typing import Literal

from app.domain.errors import ConflictError

Action = Literal["activate", "suspend", "decommission"]
Status = Literal["registered", "active", "suspended", "decommissioned"]


TRANSITIONS: Mapping[Action, tuple[frozenset[Status], Status]] = MappingProxyType(
    {
        "activate": (frozenset({"registered", "suspended"}), "active"),
        "suspend": (frozenset({"active"}), "suspended"),
        "decommission": (
            frozenset({"registered", "active", "suspended"}),
            "decommissioned",
        ),
    }
)


class InvalidStatusTransitionError(ConflictError):
    def __init__(
        self,
        current: Status,
        action: Action,
        message: str | None = None,
    ):
        self.current = current
        self.action = action
        super().__init__(
            message or f"Cannot '{action}' a terminal in status '{current}'."
        )


def next_status(current: Status, action: Action) -> Status:
    sources, target = TRANSITIONS[action]
    if current not in sources:
        raise InvalidStatusTransitionError(current, action)
    return target

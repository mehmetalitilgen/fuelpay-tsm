import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

DEFAULT_PAGE_LIMIT = 50
MAX_PAGE_LIMIT = 100


type Status = Literal["registered"]


class TerminalBase(BaseModel):
    serial_number: str
    pump_number: int


class TerminalCreate(TerminalBase):
    model_config = ConfigDict(extra="forbid")

    serial_number: str = Field(min_length=8, max_length=16, pattern=r"^[A-Z0-9]{8,16}$")
    pump_number: int = Field(ge=1, le=32, strict=False)

    @field_validator("serial_number", mode="before")
    @classmethod
    def strip_and_upper(cls, value: object) -> str:
        if isinstance(value, str):
            if not value.isascii():
                raise ValueError("serial_number must contain only A-Z and 0-9")
            return value.strip().upper()
        return value

    @field_validator("pump_number", mode="before")
    @classmethod
    def reject_bool(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("pump_number must be an integer, not a boolean")
        return value


class TerminalRead(TerminalBase):
    id: uuid.UUID
    station_id: uuid.UUID
    serial_number: str
    pump_number: int
    status: Status
    created_at: datetime


class TerminalList(BaseModel):
    items: list[TerminalRead]
    total: int
    limit: int
    offset: int

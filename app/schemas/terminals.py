import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.terminal_status import Status


class TerminalBase(BaseModel):
    serial_number: str
    pump_number: int


class TerminalCreate(TerminalBase):
    model_config = ConfigDict(extra="forbid")

    serial_number: str = Field(min_length=8, max_length=16, pattern=r"^[A-Z0-9]{8,16}$")
    pump_number: int = Field(ge=1, le=32, strict=True)

    @field_validator("serial_number", mode="before")
    @classmethod
    def strip_and_upper(cls, value: object) -> str:
        if isinstance(value, str):
            if not value.isascii():
                raise ValueError("serial_number must contain only A-Z and 0-9")
            return value.strip().upper()
        return value


class TerminalRead(TerminalBase):
    id: uuid.UUID
    station_id: uuid.UUID
    serial_number: str
    pump_number: int
    status: Status
    created_at: datetime
    status_changed_at: datetime | None = Field(default=None)
    suspension_reason: str | None = Field(default=None)


class TerminalSuspend(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    reason: str = Field(min_length=1, max_length=200)


class TerminalList(BaseModel):
    items: list[TerminalRead]
    total: int
    limit: int
    offset: int

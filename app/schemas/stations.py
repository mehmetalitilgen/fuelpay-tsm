import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_PAGE_LIMIT = 50
MAX_PAGE_LIMIT = 100


class StationBase(BaseModel):
    code: str
    name: str
    city: str


class StationCreate(StationBase):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    code: str = Field(min_length=5, pattern=r"^[0-9]{2}-[0-9]{3}$")
    name: str = Field(min_length=1, max_length=100)
    city: str = Field(min_length=1, max_length=50)


class StationRead(StationBase):
    id: uuid.UUID
    created_at: datetime


class StationList(BaseModel):
    items: list[StationRead]
    total: int
    limit: int
    offset: int

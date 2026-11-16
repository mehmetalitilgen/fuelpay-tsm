"""İstasyon API sözleşmesi: girdi, çıktı ve liste zarfı modelleri."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# Liste sayfalaması. Varsayılan FTSM-003'ten; üst sınır teslimat notunda.
DEFAULT_PAGE_LIMIT = 50
MAX_PAGE_LIMIT = 100


class StationCreate(BaseModel):
    code: str = Field(min_length=5, pattern=r"^[0-9]{2}-[0-9]{3}$")
    name: str = Field(min_length=1, max_length=100)
    city: str = Field(min_length=1, max_length=50)

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class StationRead(StationCreate):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class StationList(BaseModel):
    items: list[StationRead]
    total: int
    limit: int
    offset: int

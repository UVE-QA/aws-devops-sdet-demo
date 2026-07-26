"""Pydantic schemas for the items slice (Phase 10).

The API contract lives here, not in the route bodies, so the negative cases
are declarative and testable:

  name          required, trimmed, 1..200 chars   -> 422 when violated
  description   optional, trimmed, <= 2000 chars  -> 422 when violated
  unknown field rejected (extra="forbid")         -> 422

`extra="forbid"` is deliberate. A silently ignored field is the kind of thing
a client discovers in production; rejecting it makes the contract explicit and
gives the suite a negative case that costs nothing to maintain.

The list response is an ENVELOPE rather than a bare array. Pagination is
Phase 16; adding `limit`/`offset`/`total` to an envelope is additive, whereas
adding them to a bare array is a breaking change to every consumer and every
test written against it.
"""
from datetime import datetime
from typing import Annotated, List, Optional

from pydantic import BaseModel, ConfigDict, StringConstraints

NameStr = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
DescriptionStr = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=2000)
]


class ItemCreate(BaseModel):
    """Request body for POST /api/items."""

    model_config = ConfigDict(extra="forbid")

    name: NameStr
    description: Optional[DescriptionStr] = None


class ItemRead(BaseModel):
    """One item as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    created_at: datetime


class ItemList(BaseModel):
    """Envelope for GET /api/items."""

    items: List[ItemRead]
    count: int

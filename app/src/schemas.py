"""Pydantic schemas for the items slice (Phase 10, extended in Phase 16a).

The API contract lives here, not in the route bodies, so the negative cases
are declarative and testable:

  name          required, trimmed, 1..200 chars   -> 422 when violated
  description   optional, trimmed, <= 2000 chars  -> 422 when violated
  unknown field rejected (extra="forbid")         -> 422

`extra="forbid"` is deliberate. A silently ignored field is the kind of thing
a client discovers in production; rejecting it makes the contract explicit and
gives the suite a negative case that costs nothing to maintain.

The list response is an ENVELOPE rather than a bare array, which is what made
pagination additive when Phase 16a arrived: `count` still means "items in this
response" and `total`, `limit` and `offset` were added beside it (ADR-0031).
Had this been a bare array, every consumer and every test would have broken.
"""
from datetime import datetime
from typing import Annotated, List, Optional

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

# Page size bounds. DEFAULT_LIMIT applies when the client says nothing, so the
# endpoint is bounded by default rather than on request; MAX_LIMIT is what stops
# `?limit=1000000` from being the old unbounded endpoint with extra steps.
DEFAULT_LIMIT = 20
MAX_LIMIT = 100

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


class ItemUpdate(BaseModel):
    """Request body for PATCH /api/items/{id} — a PARTIAL update.

    Both fields default to None, which alone would make "not sent" and "sent as
    null" indistinguishable. `model_fields_set` is what separates them, and the
    route applies `model_dump(exclude_unset=True)`, so an absent field is left
    alone and an explicit null is applied (ADR-0031).

    Two things are refused rather than silently accepted:

      {}              an update that updates nothing is a client bug, and 200
                      is the answer that hides it
      {"name": null}  name is NOT NULL in the database. Accepting this would
                      turn a contract error into an IntegrityError and a 409
                      about a duplicate, which is a lie about what went wrong.
    """

    model_config = ConfigDict(extra="forbid")

    name: Optional[NameStr] = None
    description: Optional[DescriptionStr] = None

    @model_validator(mode="after")
    def at_least_one_field_and_name_not_null(self) -> "ItemUpdate":
        if not self.model_fields_set:
            raise ValueError(
                "send at least one of 'name' or 'description'; "
                "an empty patch changes nothing"
            )
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("'name' cannot be null; it is required on every item")
        return self


class ItemRead(BaseModel):
    """One item as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ItemList(BaseModel):
    """Envelope for GET /api/items.

    count  items in THIS response      -> a wrong limit shows up as count > limit
    total  rows that exist             -> a wrong count query shows up as
                                          total < count
    """

    items: List[ItemRead]
    count: int
    total: int
    limit: int
    offset: int

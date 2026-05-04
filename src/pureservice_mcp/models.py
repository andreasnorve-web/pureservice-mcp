"""Pydantic models for Pureservice entities.

These are intentionally permissive (extra='allow') because the Pureservice
API is in beta and may add fields. We model the well-known fields and let
the rest pass through.
"""
from __future__ import annotations

from datetime import datetime
from enum import IntEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class UserRole(IntEnum):
    NONE = 0
    PENDING_ACTIVATE = 1
    LOCATION_PENDING_ACTIVATE = 2
    ENDUSER = 10
    AGENT = 20
    ZONE_ADMIN = 25
    ADMINISTRATOR = 30
    SYSTEM = 50


class Visibility(IntEnum):
    VISIBLE = 0
    VISIBLE_SILENT = 1
    NOT_VISIBLE = 2


class _Base(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)


class Ticket(_Base):
    id: int | None = None
    subject: str | None = None
    description: str | None = None
    status_id: int | None = Field(default=None, alias="statusId")
    priority_id: int | None = Field(default=None, alias="priorityId")
    user_id: int | None = Field(default=None, alias="userId")
    assigned_user_id: int | None = Field(default=None, alias="assignedUserId")
    created: datetime | None = None
    modified: datetime | None = None


class User(_Base):
    id: int | None = None
    email: str | None = None
    first_name: str | None = Field(default=None, alias="firstName")
    last_name: str | None = Field(default=None, alias="lastName")
    role: int | None = None
    disabled: bool | None = None


class Status(_Base):
    id: int | None = None
    name: str | None = None
    default: bool | None = None
    request_type_id: int | None = Field(default=None, alias="requestTypeId")


def parse_list(payload: dict[str, Any], resource_key: str, model: type[BaseModel]) -> list[BaseModel]:
    """Parse a JSON:API list response into a list of models."""
    items = payload.get(resource_key, [])
    return [model.model_validate(item) for item in items]

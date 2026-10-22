"""Models reused from the Day 4 and Day 5 exercises."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class AssigneeReference(BaseModel):
    value: str | None = None
    display_value: str | None = None
    link: str | None = None


class IncidentModel(BaseModel):
    number: str
    priority: int = Field(ge=1, le=5)
    # Retain the teaching examples alongside raw ServiceNow state codes.
    state: int | Literal["open", "closed"] | None = None
    assigned_to: AssigneeReference | str | None = None
    short_description: str = ""
    sys_id: str | None = None

    @field_validator("number")
    @classmethod
    def number_starts_with_inc(cls, value: str) -> str:
        if not value.startswith("INC"):
            raise ValueError("Incident number must start with 'INC'.")
        return value

    @field_validator("state", mode="before")
    @classmethod
    def parse_state(cls, value: object) -> object:
        if value is None or value in ("open", "closed"):
            return value
        if type(value) is int:
            return value
        if isinstance(value, str) and value.isdecimal():
            return int(value)
        raise ValueError("State must be a numeric code, 'open', or 'closed'.")

    @field_validator("assigned_to", mode="before")
    @classmethod
    def empty_assignee_is_none(cls, value: object) -> object:
        return None if value == "" else value

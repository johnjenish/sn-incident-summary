"""Models for raw ServiceNow incident data."""

from enum import IntEnum

from pydantic import BaseModel, Field, field_validator


class IncidentState(IntEnum):
    NEW = 1
    IN_PROGRESS = 2
    ON_HOLD = 3
    RESOLVED = 6
    CLOSED = 7
    CANCELED = 8


class AssigneeReference(BaseModel):
    value: str | None = None
    display_value: str | None = None
    link: str | None = None


class IncidentModel(BaseModel):
    number: str
    priority: int = Field(ge=1, le=5)
    state: IncidentState
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
        if isinstance(value, IncidentState):
            return value
        if type(value) is int:
            return value
        if isinstance(value, str) and value.isdecimal():
            return int(value)
        raise ValueError("State must be a supported ServiceNow numeric state code.")

    @field_validator("assigned_to", mode="before")
    @classmethod
    def empty_assignee_is_none(cls, value: object) -> object:
        return None if value == "" else value

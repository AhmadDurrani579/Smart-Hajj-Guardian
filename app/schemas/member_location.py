
from datetime import datetime, timedelta, timezone
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class LocationUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)

    accuracy_m: float | None = Field(
        default=None,
        ge=0,
        allow_inf_nan=False,
    )

    recorded_at: datetime

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("recorded_at must include a timezone")

        now = datetime.now(timezone.utc)
        recorded_at = value.astimezone(timezone.utc)

        if recorded_at > now + timedelta(minutes=2):
            raise ValueError(
                "recorded_at cannot be more than 2 minutes in the future"
            )

        if recorded_at < now - timedelta(minutes=5):
            raise ValueError("GPS location is too old")

        return recorded_at


class LocationSharingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool


class LocationSharingResponse(BaseModel):
    group_id: int
    user_id: int
    location_sharing_enabled: bool


class MemberLocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    group_id: int
    user_id: int

    latitude: float
    longitude: float
    accuracy_m: float | None

    recorded_at: datetime


class GroupLocationsResponse(BaseModel):
    group_id: int
    locations: list[MemberLocationResponse]


from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


JourneyType = Literal["HAJJ", "UMRAH"]
MemberRole = Literal["LEADER", "MEMBER"]


class GroupCreateRequest(BaseModel):
    group_name: str = Field(min_length=1, max_length=100)
    journey_type: JourneyType

    @field_validator("group_name")
    @classmethod
    def validate_group_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Group name cannot be empty")
        return value


class GroupJoinRequest(BaseModel):
    invitation_code: str = Field(
        min_length=8,
        max_length=8,
        pattern=r"^[A-Za-z0-9]{8}$",
    )

    @field_validator("invitation_code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.upper()


class GroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    group_name: str
    leader_id: int
    invitation_code: str
    journey_type: JourneyType
    created_at: datetime


class GroupMembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    group_id: int
    user_id: int
    role: MemberRole
    location_sharing_enabled: bool
    joined_at: datetime
    is_active: bool
    left_at: datetime | None = None

class GroupUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    phone: str | None = None
    profile_image_url: str | None = None
    elderly_mode: bool


class GroupMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    group_id: int
    role: MemberRole
    location_sharing_enabled: bool
    joined_at: datetime
    is_active: bool
    left_at: datetime | None = None

    user: GroupUserResponse


class GroupDetailResponse(GroupResponse):
    members: list[GroupMemberResponse] = Field(default_factory=list)


class GroupLeaveResponse(BaseModel):
    message: str
    group_id: int
    left_at: datetime

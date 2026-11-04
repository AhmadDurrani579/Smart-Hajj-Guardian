
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DashboardUserResponse(BaseModel):
    id: int
    full_name: str
    profile_image_url: str | None = None
    elderly_mode: bool = False


class DashboardJourneyResponse(BaseModel):
    id: int
    journey_type: str
    status: str
    completed_steps: int = Field(ge=0)
    total_steps: int = Field(ge=0)
    progress_percentage: float = Field(ge=0, le=100)
    current_step_id: int | None = None
    current_step_title: str | None = None


class DashboardLeaderResponse(BaseModel):
    user_id: int
    full_name: str


class DashboardGroupResponse(BaseModel):
    id: int
    name: str
    role: str
    member_count: int = Field(ge=0)
    location_sharing_enabled: bool = False
    leader: DashboardLeaderResponse | None = None


class DashboardGroupLocationResponse(BaseModel):
    available: bool = False
    leader_distance_metres: float | None = Field(
        default=None,
        ge=0,
    )
    last_updated_at: datetime | None = None


class DashboardLatestMessageResponse(BaseModel):
    id: int
    sender_id: int
    sender_name: str
    message_text: str
    created_at: datetime


class DashboardChatResponse(BaseModel):
    group_id: int
    latest_message: DashboardLatestMessageResponse | None = None
    unread_count: int | None = Field(default=None, ge=0)


class DashboardSOSResponse(BaseModel):
    available: bool = False
    active_alert: dict | None = None


class DashboardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user: DashboardUserResponse
    journey: DashboardJourneyResponse | None = None
    group: DashboardGroupResponse | None = None
    group_location: DashboardGroupLocationResponse | None = None
    chat: DashboardChatResponse | None = None
    sos: DashboardSOSResponse = Field(
        default_factory=DashboardSOSResponse,
    )

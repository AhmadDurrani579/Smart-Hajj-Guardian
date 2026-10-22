
from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


MessageType = Literal["TEXT", "QUICK_TEXT"]


class MessageSendRequest(BaseModel):
    message_text: str = Field(
        min_length=1,
        max_length=4000,
    )

    message_type: MessageType = "TEXT"

    @field_validator("message_text")
    @classmethod
    def validate_message(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Message cannot be empty")

        return value


class MessageSenderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    profile_image_url: str | None = None


class GroupMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    group_id: int
    message_text: str
    message_type: MessageType
    created_at: datetime
    sender: MessageSenderResponse


class MessageHistoryRequest(BaseModel):
    limit: int = Field(default=30, ge=1, le=100)
    before_id: int | None = Field(default=None, gt=0)

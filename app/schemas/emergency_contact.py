from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EmergencyContactCreate(BaseModel):
    contact_name: str = Field(min_length=2, max_length=150)
    phone_number: str = Field(min_length=3, max_length=30)
    relationship: str | None = None


class EmergencyContactUpdate(BaseModel):
    contact_name: str | None = Field(default=None, min_length=2, max_length=150)
    phone_number: str | None = Field(default=None, min_length=3, max_length=30)
    relationship: str | None = None


class EmergencyContactResponse(BaseModel):
    id: int
    user_id: int
    contact_name: str
    phone_number: str
    relationship: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
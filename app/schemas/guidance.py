from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


JourneyType = Literal["HAJJ", "UMRAH"]


class GuidanceResponse(BaseModel):
    id: int
    journey_type: JourneyType
    variant: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GuidanceStepResponse(BaseModel):
    id: int
    guidance_version_id: int
    step_order: int
    title: str
    instructions: str
    location_context: str | None
    adab: str | None
    dua: str | None
    safety_notes: str | None
    source_reference: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GuidanceSourceResponse(BaseModel):
    id: int
    source_type: str
    title: str
    author: str | None
    reference_number: str | None
    source_url: str | None
    notes: str | None

    model_config = ConfigDict(from_attributes=True)

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StepCompleteRequest(BaseModel):
    client_operation_id: UUID | None = None


class StepProgressResponse(BaseModel):
    id: int
    journey_id: int
    guidance_step_id: int
    guidance_version_id: int
    status: str
    completed_at: datetime
    client_operation_id: UUID | None

    model_config = ConfigDict(from_attributes=True)


class JourneyStepStatus(BaseModel):
    step_id: int
    step_order: int
    title: str
    status: str
    completed_at: datetime | None


class JourneyProgressResponse(BaseModel):
    journey_id: int
    total_steps: int
    completed_steps: int
    progress_percentage: float
    steps: list[JourneyStepStatus]


class JourneySummaryResponse(BaseModel):
    journey_id: int
    journey_status: str
    total_steps: int
    completed_steps: int
    remaining_steps: int
    progress_percentage: float

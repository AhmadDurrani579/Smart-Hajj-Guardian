
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


JourneyType = Literal["HAJJ", "UMRAH"]
JourneyStatus = Literal["ACTIVE", "COMPLETED", "CANCELLED"]
HajjVariant = Literal["TAMATTU", "QIRAN", "IFRAD"]


class JourneyCreate(BaseModel):
    journey_type: JourneyType
    variant: HajjVariant | Literal["STANDARD"] = Field(
        default="STANDARD"
    )

    @model_validator(mode="after")
    def validate_variant(self):
        if self.journey_type == "UMRAH" and self.variant != "STANDARD":
            raise ValueError("Umrah must use the STANDARD variant")

        if self.journey_type == "HAJJ" and self.variant == "STANDARD":
            raise ValueError(
                "Select TAMATTU, QIRAN, or IFRAD for Hajj"
            )

        return self


class JourneyResponse(BaseModel):
    id: int
    user_id: int
    guidance_version_id: int
    journey_type: JourneyType
    status: JourneyStatus
    started_at: datetime
    ended_at: datetime | None

    model_config = ConfigDict(from_attributes=True)

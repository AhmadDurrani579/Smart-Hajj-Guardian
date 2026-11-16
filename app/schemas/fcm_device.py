
from pydantic import BaseModel, Field


class FCMDeviceRegisterRequest(BaseModel):
    fcm_token: str = Field(
        min_length=10,
        max_length=4096,
    )


class FCMDeviceUnregisterRequest(BaseModel):
    fcm_token: str = Field(
        min_length=10,
        max_length=4096,
    )

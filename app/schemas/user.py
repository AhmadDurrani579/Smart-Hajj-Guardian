from pydantic import BaseModel, Field


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    phone: str | None = None
    elderly_mode: bool | None = None
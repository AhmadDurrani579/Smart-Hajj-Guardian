
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.guidance import (
    GuidanceVersion,
    GuidanceStep,
    GuidanceSource,
    GuidanceStepSource,
)


class GuidanceRepository:

    def __init__(self, db: Session):
        self.db = db

    def _allow_dev_guidance(self) -> bool:
        settings = get_settings()

        return (
            settings.ENVIRONMENT == "development"
            and settings.DEBUG is True
            and settings.ALLOW_UNVERIFIED_DEV_GUIDANCE is True
        )

    def get_active_guidance(self, journey_type: str | None = None):
        statement = select(GuidanceVersion)

        if not self._allow_dev_guidance():
            statement = statement.where(
                GuidanceVersion.is_active.is_(True)
            )

        if journey_type:
            statement = statement.where(
                GuidanceVersion.journey_type == journey_type
            )

        statement = statement.order_by(
            GuidanceVersion.journey_type,
            GuidanceVersion.variant,
        )

        return self.db.scalars(statement).all()

    def get_guidance_by_id(self, guidance_id: int):
        statement = select(GuidanceVersion).where(
            GuidanceVersion.id == guidance_id
        )

        if not self._allow_dev_guidance():
            statement = statement.where(
                GuidanceVersion.is_active.is_(True)
            )

        return self.db.scalar(statement)

    def get_guidance_by_type(self, journey_type: str, variant: str):
        statement = select(GuidanceVersion).where(
            GuidanceVersion.journey_type == journey_type,
            GuidanceVersion.variant == variant,
        )

        if not self._allow_dev_guidance():
            statement = statement.where(
                GuidanceVersion.is_active.is_(True)
            )

        return self.db.scalar(statement)

    def get_guidance_steps(self, guidance_id: int):
        statement = (
            select(GuidanceStep)
            .where(GuidanceStep.guidance_version_id == guidance_id)
            .order_by(GuidanceStep.step_order)
        )

        return self.db.scalars(statement).all()

    def get_step_sources(self, step_id: int):
        statement = (
            select(GuidanceSource)
            .join(
                GuidanceStepSource,
                GuidanceSource.id == GuidanceStepSource.guidance_source_id,
            )
            .where(GuidanceStepSource.guidance_step_id == step_id)
            .order_by(GuidanceSource.id)
        )

        return self.db.scalars(statement).all()

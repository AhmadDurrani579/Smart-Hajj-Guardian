
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.guidance import GuidanceStep
from app.models.journey_progress import JourneyStepProgress


class JourneyProgressRepository:

    def __init__(self, db: Session):
        self.db = db

    def get_steps(self, guidance_version_id: int):
        statement = (
            select(GuidanceStep)
            .where(
                GuidanceStep.guidance_version_id == guidance_version_id
            )
            .order_by(GuidanceStep.step_order)
        )
        return self.db.scalars(statement).all()

    def get_completed(self, journey_id: int):
        statement = select(JourneyStepProgress).where(
            JourneyStepProgress.journey_id == journey_id
        )
        return self.db.scalars(statement).all()

    def get_step(self, step_id: int, guidance_version_id: int):
        statement = select(GuidanceStep).where(
            GuidanceStep.id == step_id,
            GuidanceStep.guidance_version_id == guidance_version_id,
        )
        return self.db.scalar(statement)

    def get_existing(self, journey_id: int, step_id: int):
        statement = select(JourneyStepProgress).where(
            JourneyStepProgress.journey_id == journey_id,
            JourneyStepProgress.guidance_step_id == step_id,
        )
        return self.db.scalar(statement)

    def get_by_operation_id(self, operation_id: UUID):
        return self.db.scalar(
            select(JourneyStepProgress).where(
                JourneyStepProgress.client_operation_id == operation_id
            )
        )

    def create(
        self,
        journey_id: int,
        step_id: int,
        guidance_version_id: int,
        operation_id: UUID | None,
    ):
        progress = JourneyStepProgress(
            journey_id=journey_id,
            guidance_step_id=step_id,
            guidance_version_id=guidance_version_id,
            status="COMPLETED",
            client_operation_id=operation_id,
        )

        self.db.add(progress)
        self.db.flush()

        return progress

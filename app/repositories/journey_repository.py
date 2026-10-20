
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.journey import Journey
from app.models.guidance import GuidanceVersion
from app.core.config import get_settings



class JourneyRepository:

    def __init__(self, db: Session):
        self.db = db

    def get_active(self, user_id: int):
        statement = select(Journey).where(
            Journey.user_id == user_id,
            Journey.status == "ACTIVE",
        )
        return self.db.scalar(statement)

    def get_by_id(self, journey_id: int, user_id: int):
        statement = select(Journey).where(
            Journey.id == journey_id,
            Journey.user_id == user_id,
        )
        return self.db.scalar(statement)

    def get_all(self, user_id: int):
        statement = (
            select(Journey)
            .where(Journey.user_id == user_id)
            .order_by(Journey.started_at.desc(), Journey.id.desc())
        )
        return self.db.scalars(statement).all()



    def get_active_guidance(self, journey_type: str, variant: str):
        settings = get_settings()

        statement = select(GuidanceVersion).where(
            GuidanceVersion.journey_type == journey_type,
            GuidanceVersion.variant == variant,
        )

        allow_dev_guidance = (
            settings.ENVIRONMENT == "development"
            and settings.DEBUG is True
            and settings.ALLOW_UNVERIFIED_DEV_GUIDANCE is True
        )

        if not allow_dev_guidance:
            statement = statement.where(
                GuidanceVersion.is_active.is_(True)
            )

        return self.db.scalar(statement)
    def create(
        self,
        user_id: int,
        journey_type: str,
        guidance_version_id: int,
    ):
        journey = Journey(
            user_id=user_id,
            journey_type=journey_type,
            guidance_version_id=guidance_version_id,
            status="ACTIVE",
        )

        self.db.add(journey)
        self.db.flush()

        return journey

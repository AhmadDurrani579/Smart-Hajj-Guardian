
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.repositories.journey_repository import JourneyRepository
from app.schemas.journey import JourneyCreate


class JourneyService:

    def __init__(self, db: Session):
        self.db = db
        self.repository = JourneyRepository(db)

    def start_journey(self, user_id: int, data: JourneyCreate):

        active_journey = self.repository.get_active(user_id)

        if active_journey:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You already have an active journey",
            )

        guidance = self.repository.get_active_guidance(
            journey_type=data.journey_type,
            variant=data.variant,
        )

        if guidance is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guidance not available for the selected journey",
            )

        try:
            journey = self.repository.create(
                user_id=user_id,
                journey_type=data.journey_type,
                guidance_version_id=guidance.id,
            )

            self.db.commit()
            self.db.refresh(journey)

            return journey

        except IntegrityError:
            self.db.rollback()

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You already have an active journey",
            )

    def get_active(self, user_id: int):
        journey = self.repository.get_active(user_id)

        if journey is None:
            raise HTTPException(
                status_code=404,
                detail="No active journey found",
            )

        return journey

    def get_all(self, user_id: int):
        return self.repository.get_all(user_id)

    def get_by_id(self, journey_id: int, user_id: int):
        journey = self.repository.get_by_id(journey_id, user_id)

        if journey is None:
            raise HTTPException(
                status_code=404,
                detail="Journey not found",
            )

        return journey

    def finish_journey(
        self,
        journey_id: int,
        user_id: int,
        new_status: str,
    ):
        journey = self.get_by_id(journey_id, user_id)

        if journey.status != "ACTIVE":
            raise HTTPException(
                status_code=409,
                detail="Only active journeys can be completed or cancelled",
            )

        journey.status = new_status
        journey.ended_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(journey)

        return journey

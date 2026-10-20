
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.repositories.journey_repository import JourneyRepository
from app.repositories.journey_progress_repository import (
    JourneyProgressRepository,
)


class JourneyProgressService:

    def __init__(self, db: Session):
        self.db = db
        self.journeys = JourneyRepository(db)
        self.progress = JourneyProgressRepository(db)

    def _get_journey(self, journey_id: int, user_id: int):
        journey = self.journeys.get_by_id(journey_id, user_id)

        if journey is None:
            raise HTTPException(404, "Journey not found")

        return journey

    def _calculate(self, journey):
        steps = self.progress.get_steps(
            journey.guidance_version_id
        )

        completed_records = self.progress.get_completed(journey.id)
        completed_map = {
            record.guidance_step_id: record
            for record in completed_records
        }

        total = len(steps)
        completed = sum(
            step.id in completed_map for step in steps
        )

        percentage = round(completed / total * 100, 2) if total else 0.0

        return steps, completed_map, total, completed, percentage

    def get_progress(self, journey_id: int, user_id: int):
        journey = self._get_journey(journey_id, user_id)

        steps, completed_map, total, completed, percentage = (
            self._calculate(journey)
        )

        return {
            "journey_id": journey.id,
            "total_steps": total,
            "completed_steps": completed,
            "progress_percentage": percentage,
            "steps": [
                {
                    "step_id": step.id,
                    "step_order": step.step_order,
                    "title": step.title,
                    "status": (
                        "COMPLETED"
                        if step.id in completed_map
                        else "UPCOMING"
                    ),
                    "completed_at": (
                        completed_map[step.id].completed_at
                        if step.id in completed_map
                        else None
                    ),
                }
                for step in steps
            ],
        }

    def get_summary(self, journey_id: int, user_id: int):
        journey = self._get_journey(journey_id, user_id)

        _, _, total, completed, percentage = (
            self._calculate(journey)
        )

        return {
            "journey_id": journey.id,
            "journey_status": journey.status,
            "total_steps": total,
            "completed_steps": completed,
            "remaining_steps": total - completed,
            "progress_percentage": percentage,
        }

    def complete_step(
        self,
        journey_id: int,
        step_id: int,
        user_id: int,
        operation_id=None,
    ):
        journey = self._get_journey(journey_id, user_id)

        if operation_id is not None:
            previous_operation = self.progress.get_by_operation_id(
                operation_id
            )

            if previous_operation is not None:
                if (
                    previous_operation.journey_id == journey_id
                    and previous_operation.guidance_step_id == step_id
                ):
                    return previous_operation

                raise HTTPException(
                    409,
                    "Operation ID was used for a different step",
                )

        existing = self.progress.get_existing(
            journey_id, step_id
        )

        if existing is not None:
            return existing

        if journey.status != "ACTIVE":
            raise HTTPException(
                409,
                "Only active journeys can record new progress",
            )

        step = self.progress.get_step(
            step_id, journey.guidance_version_id
        )

        if step is None:
            raise HTTPException(
                404,
                "Step does not belong to this journey",
            )

        try:
            record = self.progress.create(
                journey_id=journey_id,
                step_id=step_id,
                guidance_version_id=journey.guidance_version_id,
                operation_id=operation_id,
            )

            self.db.commit()
            self.db.refresh(record)
            return record

        except IntegrityError:
            self.db.rollback()

            # An overlapping request may have completed this step.
            existing = self.progress.get_existing(
                journey_id, step_id
            )

            if existing is not None:
                if operation_id is not None:
                    same_operation = (
                        self.progress.get_by_operation_id(operation_id)
                    )
                    if (
                        same_operation is not None
                        and (
                            same_operation.journey_id != journey_id
                            or same_operation.guidance_step_id != step_id
                        )
                    ):
                        raise HTTPException(
                            409,
                            "Operation ID was used for another step",
                        )
                return existing

            raise HTTPException(
                409,
                "Progress operation could not be completed",
            )

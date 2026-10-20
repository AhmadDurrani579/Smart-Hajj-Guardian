
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.guidance_repository import GuidanceRepository


class GuidanceService:

    def __init__(self, db: Session):
        self.db = db
        self.repo = GuidanceRepository(db)

    def get_all_guidance(self, journey_type: str | None = None):
        """
        Retrieve available Hajj or Umrah guidance.
        """
        return self.repo.get_active_guidance(journey_type)

    def get_guidance_by_id(self, guidance_id: int):
        """
        Retrieve a specific active guidance record.
        """
        guidance = self.repo.get_guidance_by_id(guidance_id)

        if guidance is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guidance not found or not available",
            )

        return guidance

    def get_guidance_by_type(self, journey_type: str, variant: str):
        """
        Find guidance automatically using journey type and variant.
        """
        guidance = self.repo.get_guidance_by_type(
            journey_type,
            variant,
        )

        if guidance is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guidance not available for the selected journey",
            )

        return guidance

    def get_guidance_steps(self, guidance_id: int):
        """
        Retrieve ordered steps for available guidance.
        """
        self.get_guidance_by_id(guidance_id)

        return self.repo.get_guidance_steps(guidance_id)

    def get_step_sources(self, guidance_id: int, step_id: int):
        """
        Retrieve religious references for a guidance step.
        """
        self.get_guidance_by_id(guidance_id)

        steps = self.repo.get_guidance_steps(guidance_id)

        if not any(step.id == step_id for step in steps):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Guidance step not found",
            )

        return self.repo.get_step_sources(step_id)

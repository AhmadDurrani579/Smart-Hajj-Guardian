
from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.repositories.guidance_repository import GuidanceRepository
from app.schemas.guidance import GuidanceStepResponse


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
        Retrieve the original English guidance steps.
        """
        self.get_guidance_by_id(guidance_id)

        return self.repo.get_guidance_steps(guidance_id)

    def get_localized_guidance_steps(
        self,
        guidance_id: int,
        language: Literal["en", "ur"] = "en",
    ):
        """
        Return stored English or approved Urdu guidance.

        English: guidance_steps
        Urdu: guidance_step_localizations

        No Gemini calls are made.
        """

        original_steps = self.get_guidance_steps(guidance_id)

        # English: return existing database records.
        if language == "en":
            return original_steps

        if language != "ur":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Unsupported guidance language",
            )

        if not original_steps:
            return []

        # Retrieve approved Urdu content for this version.
        query = text("""
            SELECT
                gl.guidance_step_id,
                gl.title,
                gl.instructions,
                gl.location_context,
                gl.adab,
                gl.safety_notes,
                gl.dua_arabic,
                gl.dua_transliteration,
                gl.dua_meaning

            FROM guidance_step_localizations gl

            JOIN guidance_steps gs
                ON gs.id = gl.guidance_step_id

            WHERE gs.guidance_version_id = :guidance_id
              AND gl.language = 'ur'
              AND gl.is_approved = TRUE
        """)

        rows = self.db.execute(
            query,
            {"guidance_id": guidance_id},
        ).mappings().all()

        localizations = {
            row["guidance_step_id"]: row
            for row in rows
        }

        # Never return a mixture of English and Urdu
        # if approved localizations are missing.
        missing_steps = [
            step.id
            for step in original_steps
            if step.id not in localizations
        ]

        if missing_steps:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Approved Urdu guidance is not available "
                    "for all steps of this guidance version"
                ),
            )

        results = []

        for step in original_steps:
            localized = localizations[step.id]

            original = GuidanceStepResponse.model_validate(
                step,
                from_attributes=True,
            ).model_dump()

            # Replace language-specific content.
            original["title"] = localized["title"]
            original["instructions"] = localized["instructions"]
            original["location_context"] = localized["location_context"]
            original["adab"] = localized["adab"]
            original["safety_notes"] = localized["safety_notes"]

            # Keep the original stored dua field for now.
            # Verified Arabic / translations can be added
            # to the API schema separately.
            original["dua"] = step.dua

            # Preserve actual source verification metadata.
            original["source_reference"] = step.source_reference

            results.append(original)

        return results

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


from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.guidance import (
    JourneyType,
    GuidanceResponse,
    GuidanceStepResponse,
    GuidanceSourceResponse,
)
from app.services.guidance_service import GuidanceService
from typing import Literal
from fastapi import HTTPException, Query

from app.services.guidance_generation_service import (
    GuidanceGenerationService,
)


router = APIRouter(
    prefix="/guidance",
    tags=["Guidance"],
    dependencies=[Depends(get_current_user)],
)


@router.get(
    "",
    response_model=list[GuidanceResponse],
)
def get_all_guidance(
    journey_type: JourneyType | None = None,
    db: Session = Depends(get_db),
):
    """
    Retrieve available Hajj and Umrah guidance.
    Optionally filter by journey type.
    """
    service = GuidanceService(db)

    return service.get_all_guidance(journey_type)


@router.get(
    "/{guidance_id}",
    response_model=GuidanceResponse,
)
def get_guidance(
    guidance_id: int,
    db: Session = Depends(get_db),
):
    """
    Retrieve a specific active guidance record.
    """
    service = GuidanceService(db)

    return service.get_guidance_by_id(guidance_id)



@router.get(
    "/{guidance_id}/steps",
    response_model=list[GuidanceStepResponse],
)
def get_guidance_steps(
    guidance_id: int,
    language: Literal["en", "ur"] = Query(default="en"),
    db: Session = Depends(get_db),
):
    service = GuidanceService(db)

    # Preserve existing guidance access and approval checks.
    stored_steps = service.get_guidance_steps(guidance_id)

    steps = [
        GuidanceStepResponse.model_validate(
            step,
            from_attributes=True,
        )
        for step in stored_steps
    ]

    if not steps:
        return []

    try:
        generator = GuidanceGenerationService()

        return generator.generate_steps(
            steps=steps,
            language=language,
        )

    except Exception as exc:
        import logging

        logging.getLogger(__name__).exception(
            "Gemini guidance generation failed"
        )

        raise HTTPException(
            status_code=503,
            detail="Guidance generation is temporarily unavailable",
        ) from exc


@router.get(
    "/{guidance_id}/steps/{step_id}/sources",
    response_model=list[GuidanceSourceResponse],
)
def get_guidance_step_sources(
    guidance_id: int,
    step_id: int,
    db: Session = Depends(get_db),
):
    """
    Retrieve religious references linked to a guidance step.
    """
    service = GuidanceService(db)

    return service.get_step_sources(guidance_id, step_id)

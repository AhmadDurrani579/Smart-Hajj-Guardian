from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.journey import JourneyCreate, JourneyResponse
from app.services.journey_service import JourneyService

from app.schemas.journey_progress import (
    StepCompleteRequest,
    StepProgressResponse,
    JourneyProgressResponse,
    JourneySummaryResponse,
)

from app.services.journey_progress_service import (
    JourneyProgressService,
)

router = APIRouter(
    prefix="/journeys",
    tags=["Journeys"],
)


@router.post(
    "",
    response_model=JourneyResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_journey(
    data: JourneyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return JourneyService(db).start_journey(
        current_user.id, data
    )


@router.get(
    "/active",
    response_model=JourneyResponse,
)
def get_active_journey(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return JourneyService(db).get_active(current_user.id)


@router.get(
    "",
    response_model=list[JourneyResponse],
)
def list_journeys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return JourneyService(db).get_all(current_user.id)


@router.get(
    "/{journey_id}",
    response_model=JourneyResponse,
)
def get_journey(
    journey_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return JourneyService(db).get_by_id(
        journey_id, current_user.id
    )


@router.patch(
    "/{journey_id}/complete",
    response_model=JourneyResponse,
)
def complete_journey(
    journey_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return JourneyService(db).finish_journey(
        journey_id, current_user.id, "COMPLETED"
    )


@router.patch(
    "/{journey_id}/cancel",
    response_model=JourneyResponse,
)
def cancel_journey(
    journey_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return JourneyService(db).finish_journey(
        journey_id, current_user.id, "CANCELLED"
    )


@router.get(
    "/{journey_id}/progress",
    response_model=JourneyProgressResponse,
)
def get_journey_progress(
    journey_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = JourneyProgressService(db)

    return service.get_progress(
        journey_id, current_user.id
    )


@router.post(
    "/{journey_id}/steps/{step_id}/complete",
    response_model=StepProgressResponse,
)
def complete_journey_step(
    journey_id: int,
    step_id: int,
    data: StepCompleteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = JourneyProgressService(db)

    return service.complete_step(
        journey_id=journey_id,
        step_id=step_id,
        user_id=current_user.id,
        operation_id=data.client_operation_id,
    )


@router.get(
    "/{journey_id}/summary",
    response_model=JourneySummaryResponse,
)
def get_journey_summary(
    journey_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = JourneyProgressService(db)

    return service.get_summary(
        journey_id, current_user.id
    )

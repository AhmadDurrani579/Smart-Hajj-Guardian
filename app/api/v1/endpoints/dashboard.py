
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard_service import DashboardService


router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)


@router.get(
    "",
    response_model=DashboardResponse,
)
def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return the authenticated user's Home Dashboard.

    Includes:
    - User profile
    - Active group information
    - Latest group chat message
    - Fresh, permitted GPS location summary
    - Journey progress (to be integrated)
    - SOS status (to be integrated)
    """

    service = DashboardService(db)

    return service.get_dashboard(
        user_id=current_user.id,
    )

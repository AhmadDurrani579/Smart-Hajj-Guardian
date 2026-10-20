from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import UserResponse
from app.schemas.user import UserUpdate
from app.schemas.emergency_contact import (
    EmergencyContactCreate,
    EmergencyContactUpdate,
    EmergencyContactResponse,
)
from app.services.emergency_contact_service import EmergencyContactService


router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.get("/me", response_model=UserResponse)
def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_my_profile(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repository = UserRepository(db)

    updates = data.model_dump(exclude_unset=True)

    return repository.update(current_user, updates)


@router.post(
    "/me/emergency-contacts",
    response_model=EmergencyContactResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_emergency_contact(
    data: EmergencyContactCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = EmergencyContactService(db)
    return service.create(current_user.id, data)


@router.get(
    "/me/emergency-contacts",
    response_model=list[EmergencyContactResponse],
)
def list_emergency_contacts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = EmergencyContactService(db)
    return service.get_all(current_user.id)


@router.patch(
    "/me/emergency-contacts/{contact_id}",
    response_model=EmergencyContactResponse,
)
def update_emergency_contact(
    contact_id: int,
    data: EmergencyContactUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = EmergencyContactService(db)
    return service.update(contact_id, current_user.id, data)


@router.delete(
    "/me/emergency-contacts/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_emergency_contact(
    contact_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = EmergencyContactService(db)
    service.delete(contact_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
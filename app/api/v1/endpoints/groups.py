
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User

from app.schemas.group import (
    GroupCreateRequest,
    GroupJoinRequest,
    GroupResponse,
    GroupMemberResponse,
    GroupLeaveResponse,
)

from app.services.group_service import GroupService

router = APIRouter()


@router.post(
    "",
    response_model=GroupResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_group(
    data: GroupCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return GroupService(db).create_group(
        user_id=current_user.id,
        data=data,
    )


@router.get(
    "/me",
    response_model=GroupResponse,
)
def get_my_group(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return GroupService(db).get_my_group(current_user.id)


@router.post(
    "/join",
    response_model=GroupMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
def join_group(
    data: GroupJoinRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return GroupService(db).join_group(
        user_id=current_user.id,
        invitation_code=data.invitation_code,
    )


@router.get(
    "/{group_id}",
    response_model=GroupResponse,
)
def get_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return GroupService(db).get_group(
        user_id=current_user.id,
        group_id=group_id,
    )


@router.get(
    "/{group_id}/members",
    response_model=list[GroupMemberResponse],
)
def get_group_members(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return GroupService(db).get_members(
        user_id=current_user.id,
        group_id=group_id,
    )


@router.post(
    "/{group_id}/leave",
    response_model=GroupLeaveResponse,
)
def leave_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return GroupService(db).leave_group(
        user_id=current_user.id,
        group_id=group_id,
    )


@router.delete(
    "/{group_id}/members/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_group_member(
    group_id: int,
    member_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    GroupService(db).remove_member(
        leader_user_id=current_user.id,
        group_id=group_id,
        member_id=member_id,
    )
    return None

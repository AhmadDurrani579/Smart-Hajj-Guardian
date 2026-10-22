
import secrets
import string
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.repositories.group_repository import GroupRepository
from app.schemas.group import GroupCreateRequest


class GroupService:

    def __init__(self, db: Session):
        self.db = db
        self.repository = GroupRepository(db)

    def _generate_invitation_code(self) -> str:
        alphabet = string.ascii_uppercase + string.digits

        return "".join(
            secrets.choice(alphabet)
            for _ in range(8)
        )

    def _get_active_membership(self, user_id: int):
        return self.repository.get_active_membership(user_id)

    def _require_membership(self, user_id: int, group_id: int):
        member = self._get_active_membership(user_id)

        if member is None or member.group_id != group_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not an active member of this group",
            )

        return member

    def _require_leader(self, user_id: int, group_id: int):
        member = self._require_membership(user_id, group_id)

        group = self.repository.get_by_id(group_id)

        if (
            group is None
            or member.role != "LEADER"
            or group.leader_id != user_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the group leader can perform this action",
            )

        return group

    # 1. Create Group
    def create_group(
        self,
        user_id: int,
        data: GroupCreateRequest,
    ):
        if self._get_active_membership(user_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You already belong to an active group",
            )

        invitation_code = self._generate_invitation_code()

        try:
            group = self.repository.create_group(
                group_name=data.group_name,
                leader_id=user_id,
                invitation_code=invitation_code,
                journey_type=data.journey_type,
            )

            self.repository.add_member(
                group_id=group.id,
                user_id=user_id,
                role="LEADER",
            )

            self.db.commit()
            self.db.refresh(group)

            return group

        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Could not create group. You may already "
                    "belong to a group, or the invitation code "
                    "may have collided. Please retry."
                ),
            )

    # 2. Join Group
    def join_group(self, user_id: int, invitation_code: str):
        if self._get_active_membership(user_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Leave your current group before joining another",
            )

        group = self.repository.get_by_invitation_code(
            invitation_code.upper()
        )

        if group is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid invitation code",
            )

        try:
            member = self.repository.add_member(
                group_id=group.id,
                user_id=user_id,
                role="MEMBER",
            )

            self.db.commit()
            self.db.refresh(member)

            return member

        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You already belong to an active group",
            )

    # 3. Get My Active Group
    def get_my_group(self, user_id: int):
        membership = self._get_active_membership(user_id)

        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="You do not belong to an active group",
            )

        return self.repository.get_by_id(membership.group_id)

    # 4. Get Group Details
    def get_group(self, user_id: int, group_id: int):
        self._require_membership(user_id, group_id)

        group = self.repository.get_by_id(group_id)

        if group is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Group not found",
            )

        return group

    # 5. Get Group Members
    def get_members(self, user_id: int, group_id: int):
        self._require_membership(user_id, group_id)

        return self.repository.get_active_members(group_id)

    # 6. Leave Group
    def leave_group(self, user_id: int, group_id: int):
        member = self._require_membership(user_id, group_id)

        if member.role == "LEADER":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Group leaders cannot leave directly. "
                    "Transfer leadership or close the group first."
                ),
            )

        try:
            self.repository.leave_group(member)
            self.db.commit()

            return {
                "message": "You have left the group successfully",
                "group_id": group_id,
                "left_at": member.left_at,
            }

        except Exception:
            self.db.rollback()
            raise

    # 7. Remove Group Member (Leader Only)
    def remove_member(
        self,
        leader_user_id: int,
        group_id: int,
        member_id: int,
    ):
        self._require_leader(leader_user_id, group_id)

        member = self.repository.get_active_member_by_id(
            group_id=group_id,
            member_id=member_id,
        )

        if member is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Active group member not found",
            )

        if member.role == "LEADER":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot remove the group leader",
            )

        try:
            self.repository.leave_group(member)
            self.db.commit()

            return {
                "message": "Member removed successfully",
                "group_id": group_id,
                "member_id": member_id,
            }

        except Exception:
            self.db.rollback()
            raise

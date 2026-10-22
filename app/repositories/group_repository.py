
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.group import ChatGroup, GroupMember
from app.models.user import User

class GroupRepository:

    def __init__(self, db: Session):
        self.db = db

    # Get group by ID
    def get_by_id(self, group_id: int):
        return self.db.scalar(
            select(ChatGroup).where(ChatGroup.id == group_id)
        )

    # Get group using invitation code
    def get_by_invitation_code(self, invitation_code: str):
        return self.db.scalar(
            select(ChatGroup).where(
                ChatGroup.invitation_code == invitation_code
            )
        )

    # Find user's active membership
    def get_active_membership(self, user_id: int):
        return self.db.scalar(
            select(GroupMember).where(
                GroupMember.user_id == user_id,
                GroupMember.is_active.is_(True),
            )
        )

    # Get all active members in a group

    def get_active_members(self, group_id: int):
        statement = (
            select(GroupMember, User)
            .join(User, GroupMember.user_id == User.id)
            .where(
                GroupMember.group_id == group_id,
                GroupMember.is_active.is_(True),
            )
            .order_by(GroupMember.joined_at, GroupMember.id)
        )

        results = self.db.execute(statement).all()

        return [
            {
                "id": member.id,
                "group_id": member.group_id,
                "role": member.role,
                "location_sharing_enabled": member.location_sharing_enabled,
                "joined_at": member.joined_at,
                "is_active": member.is_active,
                "left_at": member.left_at,
                "user": {
                    "id": user.id,
                    "full_name": user.full_name,
                    "email": user.email,
                    "phone": user.phone,
                    "profile_image_url": user.profile_image_url,
                    "elderly_mode": user.elderly_mode,
                },
            }
            for member, user in results
        ]

    # Create a group
    def create_group(
        self,
        group_name: str,
        leader_id: int,
        invitation_code: str,
        journey_type: str,
    ):
        group = ChatGroup(
            group_name=group_name,
            leader_id=leader_id,
            invitation_code=invitation_code,
            journey_type=journey_type,
        )

        self.db.add(group)
        self.db.flush()

        return group

    # Add a member to a group
    def add_member(
        self,
        group_id: int,
        user_id: int,
        role: str = "MEMBER",
    ):
        member = GroupMember(
            group_id=group_id,
            user_id=user_id,
            role=role,
            is_active=True,
            location_sharing_enabled=False,
        )

        self.db.add(member)
        self.db.flush()

        return member

    # Mark a member as inactive
    def leave_group(self, member: GroupMember):
        from datetime import datetime, timezone

        member.is_active = False
        member.left_at = datetime.now(timezone.utc)
        member.location_sharing_enabled = False

        self.db.flush()

        return member

    # Find an active member using membership ID
    def get_active_member_by_id(
        self,
        group_id: int,
        member_id: int,
    ):
        return self.db.scalar(
            select(GroupMember).where(
                GroupMember.id == member_id,
                GroupMember.group_id == group_id,
                GroupMember.is_active.is_(True),
            )
        )

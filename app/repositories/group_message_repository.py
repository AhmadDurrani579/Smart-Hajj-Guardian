
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.group import GroupMember
from app.models.group_message import GroupMessage
from app.models.user import User


class GroupMessageRepository:

    def __init__(self, db: Session):
        self.db = db

    # Verify that the user is an active group member
    def get_active_membership(
        self,
        group_id: int,
        user_id: int,
    ):
        statement = select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id,
            GroupMember.is_active.is_(True),
        )

        return self.db.scalar(statement)

    # Save a new message
    def create_message(
        self,
        group_id: int,
        sender_id: int,
        message_text: str,
        message_type: str = "TEXT",
    ):
        message = GroupMessage(
            group_id=group_id,
            sender_id=sender_id,
            message_text=message_text,
            message_type=message_type,
        )

        self.db.add(message)
        self.db.flush()

        return message

    # Retrieve messages, newest first
    def get_message_history(
        self,
        group_id: int,
        limit: int = 30,
        before_id: int | None = None,
    ):
        statement = (
            select(GroupMessage, User)
            .join(User, GroupMessage.sender_id == User.id)
            .where(GroupMessage.group_id == group_id)
        )

        if before_id is not None:
            statement = statement.where(
                GroupMessage.id < before_id
            )

        statement = statement.order_by(
            GroupMessage.id.desc()
        ).limit(limit)

        results = self.db.execute(statement).all()

        # Return chronological order for Android
        return [
            self._serialize_message(message, user)
            for message, user in reversed(results)
        ]

    # Get a saved message with sender information
    def get_message_by_id(self, message_id: int):
        statement = (
            select(GroupMessage, User)
            .join(User, GroupMessage.sender_id == User.id)
            .where(GroupMessage.id == message_id)
        )

        result = self.db.execute(statement).first()

        if result is None:
            return None

        message, user = result
        return self._serialize_message(message, user)

    # Build the nested sender response
    @staticmethod
    def _serialize_message(message: GroupMessage, user: User):
        return {
            "id": message.id,
            "group_id": message.group_id,
            "message_text": message.message_text,
            "message_type": message.message_type,
            "created_at": message.created_at,
            "sender": {
                "id": user.id,
                "full_name": user.full_name,
                "profile_image_url": user.profile_image_url,
            },
        }

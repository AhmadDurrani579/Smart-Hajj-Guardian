
from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.repositories.group_message_repository import GroupMessageRepository
from app.schemas.group_message import (
    MessageSendRequest,
    MessageHistoryRequest,
    GroupMessageResponse,
)


class GroupMessageService:

    def __init__(self, db: Session):
        self.db = db
        self.repository = GroupMessageRepository(db)

    def _require_active_member(self, group_id: int, user_id: int):
        member = self.repository.get_active_membership(
            group_id=group_id,
            user_id=user_id,
        )

        if member is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not an active member of this group",
            )

        return member

    def send_message(
        self,
        group_id: int,
        user_id: int,
        data: MessageSendRequest,
    ) -> GroupMessageResponse:

        self._require_active_member(group_id, user_id)

        try:
            message = self.repository.create_message(
                group_id=group_id,
                sender_id=user_id,
                message_text=data.message_text,
                message_type=data.message_type,
            )

            message_id = message.id

            self.db.commit()

            saved_message = self.repository.get_message_by_id(
                message_id
            )

            if saved_message is None:
                raise RuntimeError("Saved message not found")

            return GroupMessageResponse.model_validate(
                saved_message
            )

        except SQLAlchemyError:
            self.db.rollback()
            raise

    def get_history(
        self,
        group_id: int,
        user_id: int,
        data: MessageHistoryRequest,
    ) -> list[GroupMessageResponse]:

        self._require_active_member(group_id, user_id)

        messages = self.repository.get_message_history(
            group_id=group_id,
            limit=data.limit,
            before_id=data.before_id,
        )

        return [
            GroupMessageResponse.model_validate(message)
            for message in messages
        ]

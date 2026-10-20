from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.repositories.emergency_contact_repository import (
    EmergencyContactRepository,
)


class EmergencyContactService:

    def __init__(self, db: Session):
        self.db = db
        self.repository = EmergencyContactRepository(db)

    def create(self, user_id: int, data):
        contact = self.repository.create(user_id, data)
        self.db.commit()
        self.db.refresh(contact)
        return contact

    def get_all(self, user_id: int):
        return self.repository.get_all(user_id)

    def update(self, contact_id: int, user_id: int, data):
        contact = self.repository.get_by_id(contact_id, user_id)

        if not contact:
            raise HTTPException(
                status_code=404,
                detail="Emergency contact not found",
            )

        updates = data.model_dump(exclude_unset=True)

        for field, value in updates.items():
            setattr(contact, field, value)

        self.db.commit()
        self.db.refresh(contact)

        return contact

    def delete(self, contact_id: int, user_id: int):
        contact = self.repository.get_by_id(contact_id, user_id)

        if not contact:
            raise HTTPException(
                status_code=404,
                detail="Emergency contact not found",
            )

        self.repository.delete(contact)
        self.db.commit()
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.emergency_contact import EmergencyContact


class EmergencyContactRepository:

    def __init__(self, db: Session):
        self.db = db

    def create(self, user_id: int, data):
        contact = EmergencyContact(
            user_id=user_id,
            **data.model_dump(),
        )
        self.db.add(contact)
        self.db.flush()
        return contact

    def get_all(self, user_id: int):
        statement = (
            select(EmergencyContact)
            .where(EmergencyContact.user_id == user_id)
            .order_by(EmergencyContact.id)
        )
        return self.db.scalars(statement).all()

    def get_by_id(self, contact_id: int, user_id: int):
        statement = select(EmergencyContact).where(
            EmergencyContact.id == contact_id,
            EmergencyContact.user_id == user_id,
        )
        return self.db.scalar(statement)

    def delete(self, contact):
        self.db.delete(contact)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:

    def __init__(self, db: Session):
        self.db = db

    def get_by_email(self, email: str) -> User | None:
        statement = select(User).where(User.email == email)

        return self.db.scalar(statement)

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def create(
        self,
        full_name: str,
        email: str,
        password_hash: str,
        phone: str | None,
        elderly_mode: bool,
    ) -> User:

        user = User(
            full_name=full_name,
            email=email,
            password_hash=password_hash,
            phone=phone,
            elderly_mode=elderly_mode,
        )

        self.db.add(user)
        self.db.flush()

        return user

    def update(self, user, updates: dict):
        for field, value in updates.items():
            setattr(user, field, value)

        self.db.commit()
        self.db.refresh(user)

        return user
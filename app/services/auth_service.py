from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest


class AuthService:

    def __init__(self, db: Session):
        self.db = db
        self.user_repository = UserRepository(db)

    def register(self, data: RegisterRequest):
        email = str(data.email).lower()

        existing_user = self.user_repository.get_by_email(email)

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        password_hash = hash_password(data.password)

        try:
            user = self.user_repository.create(
                full_name=data.full_name.strip(),
                email=email,
                password_hash=password_hash,
                phone=data.phone,
                elderly_mode=data.elderly_mode,
            )

            self.db.commit()
            self.db.refresh(user)

            return user

        except IntegrityError:
            self.db.rollback()

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

    def login(self, data: LoginRequest):
        email = str(data.email).lower()

        user = self.user_repository.get_by_email(email)

        if user is None or not verify_password(
            data.password,
            user.password_hash,
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if user.account_status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is not active",
            )

        access_token = create_access_token(user.id)

        return {
            "access_token": access_token,
            "token_type": "bearer",
        }
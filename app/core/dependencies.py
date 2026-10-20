import jwt
from jwt.exceptions import InvalidTokenError

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository


settings = get_settings()

bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:

    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["sub", "exp", "iat"]},
        )

        if payload.get("type") != "access":
            raise credentials_error

        user_id = int(payload["sub"])

    except (InvalidTokenError, ValueError, TypeError):
        raise credentials_error

    user_repository = UserRepository(db)

    user = user_repository.get_by_id(user_id)

    if user is None or user.account_status != "ACTIVE":
        raise credentials_error

    return user
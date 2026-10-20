from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    
    full_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String,
        nullable=False,
        unique=True,
    )

    password_hash: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    phone: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    profile_image_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    elderly_mode: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    account_status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="ACTIVE",
        server_default="ACTIVE",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
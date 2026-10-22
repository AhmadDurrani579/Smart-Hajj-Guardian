
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Identity,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ChatGroup(Base):
    __tablename__ = "chat_groups"

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )

    group_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    leader_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    invitation_code: Mapped[str] = mapped_column(
        String(8),
        unique=True,
        nullable=False,
    )

    journey_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )


class GroupMember(Base):
    __tablename__ = "group_members"

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )

    group_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("chat_groups.id", ondelete="CASCADE"),
        nullable=False,
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        String,
        nullable=False,
        server_default=text("'MEMBER'"),
    )

    location_sharing_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )

    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text("true"),
        nullable=False,
    )

    left_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

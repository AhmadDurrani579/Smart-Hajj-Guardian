from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Double,
    ForeignKey,
    Identity,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MemberLocation(Base):
    __tablename__ = "member_locations"

    __table_args__ = (
        UniqueConstraint(
            "group_member_id",
            name="uq_member_locations_group_member_id",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=False),
        primary_key=True,
    )

    group_member_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("group_members.id", ondelete="RESTRICT"),
        nullable=False,
    )

    latitude: Mapped[float] = mapped_column(
        Double,
        nullable=False,
    )

    longitude: Mapped[float] = mapped_column(
        Double,
        nullable=False,
    )

    accuracy_m: Mapped[float | None] = mapped_column(
        Double,
        nullable=True,
    )

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
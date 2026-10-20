
from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class JourneyStepProgress(Base):
    __tablename__ = "journey_step_progress"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )

    journey_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )

    guidance_step_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )

    guidance_version_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )

    status: Mapped[str] = mapped_column(
        String, nullable=False, server_default="COMPLETED"
    )

    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    client_operation_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
        unique=True,
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["journey_id", "guidance_version_id"],
            ["journeys.id", "journeys.guidance_version_id"],
        ),
        ForeignKeyConstraint(
            ["guidance_step_id", "guidance_version_id"],
            ["guidance_steps.id", "guidance_steps.guidance_version_id"],
        ),
        UniqueConstraint(
            "journey_id",
            "guidance_step_id",
        ),
    )

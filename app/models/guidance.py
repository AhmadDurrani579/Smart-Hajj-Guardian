from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GuidanceVersion(Base):
    __tablename__ = "guidance_versions"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )

    journey_type: Mapped[str] = mapped_column(String, nullable=False)
    variant: Mapped[str] = mapped_column(String, nullable=False)

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class GuidanceStep(Base):
    __tablename__ = "guidance_steps"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )

    guidance_version_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("guidance_versions.id"),
        nullable=False,
    )

    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    location_context: Mapped[str | None] = mapped_column(Text)
    adab: Mapped[str | None] = mapped_column(Text)
    dua: Mapped[str | None] = mapped_column(Text)
    safety_notes: Mapped[str | None] = mapped_column(Text)
    source_reference: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class GuidanceSource(Base):
    __tablename__ = "guidance_sources"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )

    source_type: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    author: Mapped[str | None] = mapped_column(String)
    reference_number: Mapped[str | None] = mapped_column(String)
    source_url: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class GuidanceStepSource(Base):
    __tablename__ = "guidance_step_sources"

    guidance_step_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("guidance_steps.id"),
        primary_key=True,
    )

    guidance_source_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("guidance_sources.id"),
        primary_key=True,
    )

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.group import GroupMember
from app.models.member_location import MemberLocation


class MemberLocationRepository:

    def __init__(self, db: Session):
        self.db = db

    def get_active_membership(
        self,
        user_id: int,
        group_id: int | None = None,
    ) -> GroupMember | None:
        stmt = select(GroupMember).where(
            GroupMember.user_id == user_id,
            GroupMember.is_active.is_(True),
        )

        if group_id is not None:
            stmt = stmt.where(GroupMember.group_id == group_id)

        return self.db.scalar(stmt)

    def set_location_sharing(
        self,
        membership: GroupMember,
        enabled: bool,
    ) -> GroupMember:
        membership.location_sharing_enabled = enabled

        if not enabled:
            self.delete_location(membership.id)

        self.db.flush()
        return membership

    def upsert_location(
        self,
        group_member_id: int,
        latitude: float,
        longitude: float,
        accuracy_m: float | None,
        recorded_at: datetime,
    ) -> MemberLocation | None:

        stmt = insert(MemberLocation).values(
            group_member_id=group_member_id,
            latitude=latitude,
            longitude=longitude,
            accuracy_m=accuracy_m,
            recorded_at=recorded_at,
            updated_at=datetime.now(timezone.utc),
        )

        stmt = stmt.on_conflict_do_update(
            index_elements=["group_member_id"],
            set_={
                "latitude": stmt.excluded.latitude,
                "longitude": stmt.excluded.longitude,
                "accuracy_m": stmt.excluded.accuracy_m,
                "recorded_at": stmt.excluded.recorded_at,
                "updated_at": datetime.now(timezone.utc),
            },
            where=MemberLocation.recorded_at < stmt.excluded.recorded_at,
        ).returning(MemberLocation.id)

        location_id = self.db.scalar(stmt)

        if location_id is None:
            return None

        self.db.flush()

        return self.db.get(
            MemberLocation,
            location_id,
            populate_existing=True,
        )

    def get_group_locations(
        self,
        group_id: int,
        max_age_minutes: int = 5,
    ) -> list[tuple[GroupMember, MemberLocation]]:

        cutoff = datetime.now(timezone.utc) - timedelta(
            minutes=max_age_minutes
        )

        stmt = (
            select(GroupMember, MemberLocation)
            .join(
                MemberLocation,
                MemberLocation.group_member_id == GroupMember.id,
            )
            .where(
                GroupMember.group_id == group_id,
                GroupMember.is_active.is_(True),
                GroupMember.location_sharing_enabled.is_(True),
                MemberLocation.recorded_at >= cutoff,
            )
            .order_by(MemberLocation.recorded_at.desc())
        )

        return list(self.db.execute(stmt).all())

    def delete_location(
        self,
        group_member_id: int,
    ) -> None:

        stmt = delete(MemberLocation).where(
            MemberLocation.group_member_id == group_member_id
        )

        self.db.execute(stmt)

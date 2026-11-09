
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.group import GroupMember
from app.repositories.member_location_repository import (
    MemberLocationRepository,
)
from app.schemas.member_location import (
    GroupLocationsResponse,
    LocationSharingRequest,
    LocationSharingResponse,
    LocationUpdateRequest,
    MemberLocationResponse,
)


class MemberLocationService:

    def __init__(self, db: Session):
        self.db = db
        self.repository = MemberLocationRepository(db)

    def _get_locked_membership(
        self,
        user_id: int,
        group_id: int,
    ) -> GroupMember:
        stmt = (
            select(GroupMember)
            .where(
                GroupMember.user_id == user_id,
                GroupMember.group_id == group_id,
                GroupMember.is_active.is_(True),
            )
            .with_for_update()
        )

        membership = self.db.scalar(stmt)

        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not an active member of this group",
            )

        return membership

    def update_sharing(
        self,
        user_id: int,
        group_id: int,
        data: LocationSharingRequest,
    ) -> LocationSharingResponse:

        try:
            membership = self._get_locked_membership(
                user_id=user_id,
                group_id=group_id,
            )

            self.repository.set_location_sharing(
                membership=membership,
                enabled=data.enabled,
            )

            response = LocationSharingResponse(
                group_id=group_id,
                user_id=user_id,
                location_sharing_enabled=data.enabled,
            )

            self.db.commit()
            return response

        except Exception:
            self.db.rollback()
            raise

    def update_location(
        self,
        user_id: int,
        group_id: int,
        data: LocationUpdateRequest,
    ) -> MemberLocationResponse:

        try:
            membership = self._get_locked_membership(
                user_id=user_id,
                group_id=group_id,
            )

            if not membership.location_sharing_enabled:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=(
                        "Enable location sharing before "
                        "sending GPS updates"
                    ),
                )

            location = self.repository.upsert_location(
                group_member_id=membership.id,
                latitude=data.latitude,
                longitude=data.longitude,
                accuracy_m=data.accuracy_m,
                recorded_at=data.recorded_at,
            )

            if location is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A newer GPS location has already been saved",
                )

            response = MemberLocationResponse(
                group_id=group_id,
                user_id=user_id,
                latitude=location.latitude,
                longitude=location.longitude,
                accuracy_m=location.accuracy_m,
                recorded_at=location.recorded_at,
            )

            self.db.commit()
            return response

        except Exception:
            self.db.rollback()
            raise

    def get_group_locations(
        self,
        user_id: int,
        group_id: int,
    ) -> GroupLocationsResponse:

        membership = self.repository.get_active_membership(
            user_id=user_id,
            group_id=group_id,
        )

        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not an active member of this group",
            )

        rows = self.repository.get_group_locations(
            group_id=group_id,
            max_age_minutes=5,
        )

        locations = [
            MemberLocationResponse(
                group_id=group_id,
                user_id=member.user_id,
                latitude=location.latitude,
                longitude=location.longitude,
                accuracy_m=location.accuracy_m,
                recorded_at=location.recorded_at,
            )
            for member, location in rows
        ]

        return GroupLocationsResponse(
            group_id=group_id,
            locations=locations,
        )

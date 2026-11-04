
from math import asin, cos, radians, sin, sqrt

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.dashboard_repository import (
    DashboardRepository,
)

from app.schemas.dashboard import (
    DashboardResponse,
    DashboardUserResponse,
    DashboardGroupResponse,
    DashboardLeaderResponse,
    DashboardGroupLocationResponse,
    DashboardChatResponse,
    DashboardLatestMessageResponse,
    DashboardSOSResponse,
)


class DashboardService:

    def __init__(self, db: Session):
        self.db = db
        self.repository = DashboardRepository(db)

    @staticmethod
    def calculate_distance(
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:
        """
        Calculate approximate distance in metres
        between two GPS coordinates using Haversine.
        """
        earth_radius = 6371000

        latitude_difference = radians(lat2 - lat1)
        longitude_difference = radians(lon2 - lon1)

        a = (
            sin(latitude_difference / 2) ** 2
            + cos(radians(lat1))
            * cos(radians(lat2))
            * sin(longitude_difference / 2) ** 2
        )

        a = min(1.0, max(0.0, a))

        return round(
            2 * earth_radius * asin(sqrt(a)),
            2,
        )

    def get_dashboard(
        self,
        user_id: int,
    ) -> DashboardResponse:

        # -------------------------------------
        # 1. User profile
        # -------------------------------------

        user = self.repository.get_user(user_id)

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        dashboard_user = DashboardUserResponse(
            id=user["id"],
            full_name=user["full_name"],
            profile_image_url=user["profile_image_url"],
            elderly_mode=user["elderly_mode"],
        )

        # -------------------------------------
        # 2. Active group
        # -------------------------------------

        group = self.repository.get_active_group(
            user_id
        )

        dashboard_group = None
        dashboard_chat = None
        dashboard_location = None

        if group is not None:

            group_id = group["id"]
            leader_id = group["leader_id"]

            dashboard_group = DashboardGroupResponse(
                id=group_id,
                name=group["name"],
                role=group["role"],
                member_count=group["member_count"],
                location_sharing_enabled=(
                    group["location_sharing_enabled"]
                ),
                leader=DashboardLeaderResponse(
                    user_id=leader_id,
                    full_name=group["leader_name"],
                ),
            )

            # ---------------------------------
            # 3. Latest chat message
            # ---------------------------------

            latest_message = (
                self.repository.get_latest_message(
                    group_id
                )
            )

            message_response = None

            if latest_message is not None:
                message_response = (
                    DashboardLatestMessageResponse(
                        id=latest_message["id"],
                        sender_id=latest_message["sender_id"],
                        sender_name=latest_message["sender_name"],
                        message_text=latest_message["message_text"],
                        created_at=latest_message["created_at"],
                    )
                )

            dashboard_chat = DashboardChatResponse(
                group_id=group_id,
                latest_message=message_response,
                unread_count=None,
            )

            # ---------------------------------
            # 4. Group location
            # ---------------------------------

            rows = (
                self.repository.get_member_locations(
                    group_id
                )
            )

            locations_by_user = {
                item["user_id"]: item
                for item in rows
            }

            my_location = locations_by_user.get(
                user_id
            )

            leader_location = locations_by_user.get(
                leader_id
            )

            distance = None
            last_updated = None

            if leader_location is not None:
                last_updated = leader_location[
                    "recorded_at"
                ]

            # Both users must have shared a
            # recent location to compute distance.
            if (
                my_location is not None
                and leader_location is not None
            ):
                distance = self.calculate_distance(
                    my_location["latitude"],
                    my_location["longitude"],
                    leader_location["latitude"],
                    leader_location["longitude"],
                )

                last_updated = min(
                    my_location["recorded_at"],
                    leader_location["recorded_at"],
                )

            dashboard_location = (
                DashboardGroupLocationResponse(
                    available=leader_location is not None,
                    leader_distance_metres=distance,
                    last_updated_at=last_updated,
                )
            )

        # -------------------------------------
        # 5. Final Dashboard
        # -------------------------------------

        return DashboardResponse(
            user=dashboard_user,
            journey=None,
            group=dashboard_group,
            group_location=dashboard_location,
            chat=dashboard_chat,
            sos=DashboardSOSResponse(
                available=False,
                active_alert=None,
            ),
        )

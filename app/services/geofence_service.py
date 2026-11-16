
from datetime import datetime
from math import asin, cos, radians, sin, sqrt

from sqlalchemy import text
from sqlalchemy.orm import Session


GEOFENCE_RADIUS_M = 50
HYSTERESIS_M = 5
MAX_ACCURACY_M = 50.0


class GeofenceService:

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def distance_metres(
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:
        earth_radius = 6371000.0

        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)

        a = (
            sin(dlat / 2) ** 2
            + cos(radians(lat1))
            * cos(radians(lat2))
            * sin(dlon / 2) ** 2
        )

        return 2 * earth_radius * asin(
            sqrt(min(1.0, max(0.0, a)))
        )

    def evaluate_group(self, group_id: int) -> tuple[int, list[dict]]:
        """
        Evaluate the latest locations for an entire group.

        Returns:
            (leader_user_id, geofence_events)

        Only returns transition events after database commit.
        """

        try:
            # Serialize geofence evaluations for this group,
            # including evaluations triggered by leader movement.
            group = self.db.execute(
                text("""
                    SELECT id, leader_id
                    FROM chat_groups
                    WHERE id = :group_id
                    FOR UPDATE
                """),
                {"group_id": group_id},
            ).mappings().first()

            if group is None:
                self.db.rollback()
                return 0, []

            leader_id = group["leader_id"]

            # Only use fresh locations from consenting,
            # active group members.
            members = self.db.execute(
                text("""
                    SELECT
                        gm.id AS group_member_id,
                        gm.user_id,
                        gm.location_sharing_enabled,
                        ml.latitude,
                        ml.longitude,
                        ml.accuracy_m,
                        ml.recorded_at
                    FROM group_members gm

                    LEFT JOIN member_locations ml
                        ON ml.group_member_id = gm.id
                       AND ml.recorded_at >=
                           NOW() - INTERVAL '5 minutes'
                       AND ml.recorded_at <=
                           NOW() + INTERVAL '2 minutes'

                    WHERE gm.group_id = :group_id
                      AND gm.is_active = TRUE
                    ORDER BY gm.id
                """),
                {"group_id": group_id},
            ).mappings().all()

            leader = next(
                (
                    member
                    for member in members
                    if member["user_id"] == leader_id
                    and member["location_sharing_enabled"]
                    and member["latitude"] is not None
                ),
                None,
            )

            # Read existing state while holding the group lock.
            existing = self.db.execute(
                text("""
                    SELECT s.group_member_id, s.state
                    FROM group_geofence_states s
                    JOIN group_members gm
                        ON gm.id = s.group_member_id
                    WHERE gm.group_id = :group_id
                """),
                {"group_id": group_id},
            ).mappings().all()

            old_states = {
                row["group_member_id"]: row["state"]
                for row in existing
            }

            events = []

            for member in members:
                # The leader is the moving centre,
                # not a person measured against themselves.
                if member["user_id"] == leader_id:
                    continue

                member_id = member["group_member_id"]
                old_state = old_states.get(
                    member_id,
                    "UNKNOWN",
                )

                new_state = "UNKNOWN"
                distance = None
                definitive = False

                valid_member = (
                    member["location_sharing_enabled"]
                    and member["latitude"] is not None
                    and member["longitude"] is not None
                )

                if leader is not None and valid_member:
                    leader_accuracy = leader["accuracy_m"]
                    member_accuracy = member["accuracy_m"]

                    # Unknown accuracy means insufficient
                    # information to produce a reliable alert.
                    if (
                        leader_accuracy is not None
                        and member_accuracy is not None
                        and 0 <= leader_accuracy <= MAX_ACCURACY_M
                        and 0 <= member_accuracy <= MAX_ACCURACY_M
                    ):
                        distance = self.distance_metres(
                            leader["latitude"],
                            leader["longitude"],
                            member["latitude"],
                            member["longitude"],
                        )

                        uncertainty = (
                            leader_accuracy + member_accuracy
                        )

                        # Clear evidence that the member is
                        # beyond the 500m geofence.
                        if (
                            distance - uncertainty
                            > GEOFENCE_RADIUS_M + HYSTERESIS_M
                        ):
                            new_state = "OUTSIDE"
                            definitive = True

                        # Clear evidence that the member is
                        # safely inside the boundary.
                        elif (
                            distance + uncertainty
                            < GEOFENCE_RADIUS_M - HYSTERESIS_M
                        ):
                            new_state = "INSIDE"
                            definitive = True

                        else:
                            # Uncertain boundary reading:
                            # retain the previous state,
                            # but do not produce an alert.
                            new_state = old_state

                # Persist the new evaluation.
                self.db.execute(
                    text("""
                        INSERT INTO group_geofence_states (
                            group_member_id,
                            state,
                            distance_m,
                            evaluated_at
                        )
                        VALUES (
                            :member_id,
                            :state,
                            :distance,
                            NOW()
                        )
                        ON CONFLICT (group_member_id)
                        DO UPDATE SET
                            state = EXCLUDED.state,
                            distance_m = EXCLUDED.distance_m,
                            evaluated_at = NOW()
                    """),
                    {
                        "member_id": member_id,
                        "state": new_state,
                        "distance": distance,
                    },
                )

                if not definitive or new_state == old_state:
                    continue

                event_type = None

                if old_state == "INSIDE" and new_state == "OUTSIDE":
                    event_type = "GEOFENCE_EXITED"

                elif old_state == "OUTSIDE" and new_state == "INSIDE":
                    event_type = "GEOFENCE_ENTERED"

                elif old_state == "UNKNOWN" and new_state == "OUTSIDE":
                    event_type = "GEOFENCE_OUTSIDE"

                if event_type is not None:
                    events.append({
                        "type": event_type,
                        "data": {
                            "group_id": group_id,
                            "user_id": member["user_id"],
                            "leader_user_id": leader_id,
                            "distance_m": round(distance, 2),
                            "radius_m": GEOFENCE_RADIUS_M,
                            "state": new_state,
                        },
                    })

            self.db.commit()
            return leader_id, events

        except Exception:
            self.db.rollback()
            raise


    
    def get_group_distance_status(
        self,
        group_id: int,
        user_id: int,
    ) -> dict:
        # Only active group members may request distances.
        requester = self.db.execute(
            text("""
                SELECT id
                FROM group_members
                WHERE group_id = :group_id
                  AND user_id = :user_id
                  AND is_active = TRUE
                LIMIT 1
            """),
            {
                "group_id": group_id,
                "user_id": user_id,
            },
        ).first()

        if requester is None:
            raise PermissionError(
                "Not an active member of this group"
            )

        group = self.db.execute(
            text("""
                SELECT leader_id
                FROM chat_groups
                WHERE id = :group_id
            """),
            {"group_id": group_id},
        ).mappings().first()

        if group is None:
            raise ValueError("Group not found")

        leader_id = group["leader_id"]

        rows = self.db.execute(
            text("""
                SELECT
                    gm.id AS group_member_id,
                    gm.user_id,
                    gm.location_sharing_enabled,
                    ml.latitude,
                    ml.longitude,
                    ml.accuracy_m,
                    ml.recorded_at,
                    gs.state AS saved_state,
                    gs.evaluated_at

                FROM group_members gm

                LEFT JOIN member_locations ml
                    ON ml.group_member_id = gm.id

                LEFT JOIN group_geofence_states gs
                    ON gs.group_member_id = gm.id

                WHERE gm.group_id = :group_id
                  AND gm.is_active = TRUE

                ORDER BY gm.user_id
            """),
            {"group_id": group_id},
        ).mappings().all()

        # Fresh, consenting locations only.
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=5)
        future_limit = now + timedelta(minutes=2)

        def valid_location(row):
            if row is None:
                return False

            timestamp = row["recorded_at"]

            return (
                row["location_sharing_enabled"]
                and row["latitude"] is not None
                and row["longitude"] is not None
                and timestamp is not None
                and cutoff <= timestamp <= future_limit
            )

        leader = next(
            (
                row for row in rows
                if row["user_id"] == leader_id
                and valid_location(row)
            ),
            None,
        )

        result_members = []

        for member in rows:
            if member["user_id"] == leader_id:
                continue

            distance = None
            state = "UNKNOWN"

            if leader is not None and valid_location(member):
                distance = round(
                    self.distance_metres(
                        leader["latitude"],
                        leader["longitude"],
                        member["latitude"],
                        member["longitude"],
                    ),
                    2,
                )

                # Use the persisted geofence decision.
                # Do not substitute a simple 500m threshold:
                # evaluate_group() accounts for GPS uncertainty
                # and the 20m hysteresis buffer.
                accuracy_ok = (
                    leader["accuracy_m"] is not None
                    and member["accuracy_m"] is not None
                    and 0 <= leader["accuracy_m"] <= MAX_ACCURACY_M
                    and 0 <= member["accuracy_m"] <= MAX_ACCURACY_M
                )

                evaluated_at = member["evaluated_at"]

                if (
                    accuracy_ok
                    and evaluated_at is not None
                    and evaluated_at >= leader["recorded_at"]
                    and evaluated_at >= member["recorded_at"]
                    and member["saved_state"] in (
                        "INSIDE", "OUTSIDE"
                    )
                ):
                    state = member["saved_state"]

            result_members.append({
                "user_id": member["user_id"],
                "distance_m": distance,
                "state": state,
            })

        return {
            "group_id": group_id,
            "leader_user_id": leader_id,
            "radius_m": GEOFENCE_RADIUS_M,
            "leader_location_available": leader is not None,
            "members": result_members,
        }

    
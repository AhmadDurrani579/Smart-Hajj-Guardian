
from sqlalchemy import text
from sqlalchemy.orm import Session


class DashboardRepository:

    def __init__(self, db: Session):
        self.db = db

    # -----------------------------------------
    # 1. Logged-in user
    # -----------------------------------------

    def get_user(self, user_id: int):
        stmt = text("""
            SELECT
                id,
                full_name,
                profile_image_url,
                elderly_mode
            FROM users
            WHERE id = :user_id
        """)

        return self.db.execute(
            stmt,
            {"user_id": user_id},
        ).mappings().first()

    # -----------------------------------------
    # 2. Active group membership
    # -----------------------------------------

    def get_active_group(self, user_id: int):
        stmt = text("""
            SELECT
                cg.id,
                cg.group_name AS name,
                gm.role,
                gm.location_sharing_enabled,
                cg.leader_id,
                leader.full_name AS leader_name,

                (
                    SELECT COUNT(*)
                    FROM group_members members
                    WHERE members.group_id = cg.id
                      AND members.is_active = TRUE
                ) AS member_count

            FROM group_members gm

            JOIN chat_groups cg
                ON cg.id = gm.group_id

            JOIN users leader
                ON leader.id = cg.leader_id

            WHERE gm.user_id = :user_id
              AND gm.is_active = TRUE

            LIMIT 1
        """)

        return self.db.execute(
            stmt,
            {"user_id": user_id},
        ).mappings().first()

    # -----------------------------------------
    # 3. Latest group message
    # -----------------------------------------

    def get_latest_message(self, group_id: int):
        stmt = text("""
            SELECT
                msg.id,
                msg.sender_id,
                sender.full_name AS sender_name,
                msg.message_text,
                msg.created_at

            FROM group_messages msg

            JOIN users sender
                ON sender.id = msg.sender_id

            WHERE msg.group_id = :group_id

            ORDER BY msg.id DESC
            LIMIT 1
        """)

        return self.db.execute(
            stmt,
            {"group_id": group_id},
        ).mappings().first()

    # -----------------------------------------
    # 4. Latest permitted GPS locations
    # -----------------------------------------

    def get_member_locations(self, group_id: int):
        stmt = text("""
            SELECT
                gm.user_id,
                ml.latitude,
                ml.longitude,
                ml.accuracy_m,
                ml.recorded_at

            FROM group_members gm

            JOIN member_locations ml
                ON ml.group_member_id = gm.id

            WHERE gm.group_id = :group_id
              AND gm.is_active = TRUE
              AND gm.location_sharing_enabled = TRUE
              AND ml.recorded_at >= NOW() - INTERVAL '5 minutes'
        """)

        return self.db.execute(
            stmt,
            {"group_id": group_id},
        ).mappings().all()

    # -----------------------------------------
    # 5. Active journey
    # -----------------------------------------

    def get_active_journey(self, user_id: int):
        stmt = text("""
            SELECT
                j.id,
                j.user_id,
                j.guidance_version_id,
                j.journey_type,
                j.status,
                j.started_at

            FROM journeys j

            WHERE j.user_id = :user_id
              AND j.status = 'ACTIVE'

            ORDER BY j.started_at DESC, j.id DESC
            LIMIT 1
        """)

        return self.db.execute(
            stmt,
            {"user_id": user_id},
        ).mappings().first()

    # -----------------------------------------
    # 6. Guidance steps for journey
    # -----------------------------------------

    def get_journey_steps(self, guidance_version_id: int):
        stmt = text("""
            SELECT
                gs.id,
                gs.step_order,
                gs.title

            FROM guidance_steps gs

            WHERE gs.guidance_version_id = :version_id

            ORDER BY gs.step_order, gs.id
        """)

        return self.db.execute(
            stmt,
            {"version_id": guidance_version_id},
        ).mappings().all()

    # -----------------------------------------
    # 7. Completed journey step IDs
    # -----------------------------------------

    def get_completed_step_ids(
        self,
        journey_id: int,
        guidance_version_id: int,
    ) -> set[int]:

        stmt = text("""
            SELECT DISTINCT
                jsp.guidance_step_id

            FROM journey_step_progress jsp

            WHERE jsp.journey_id = :journey_id
              AND jsp.guidance_version_id = :version_id
              AND jsp.status = 'COMPLETED'
        """)

        rows = self.db.execute(
            stmt,
            {
                "journey_id": journey_id,
                "version_id": guidance_version_id,
            },
        ).scalars().all()

        return set(rows)

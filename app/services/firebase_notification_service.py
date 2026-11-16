
import base64
import json
import logging
from functools import lru_cache

import firebase_admin
from firebase_admin import credentials, messaging

from app.core.config import get_settings
from sqlalchemy import text
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_firebase_app():
    settings = get_settings()

    encoded = settings.FIREBASE_SERVICE_ACCOUNT_JSON_BASE64

    if not encoded:
        raise RuntimeError(
            "Firebase credentials are not configured"
        )

    service_account = json.loads(
        base64.b64decode(
            encoded,
            validate=True,
        ).decode("utf-8")
    )

    if (
        service_account.get("type") != "service_account"
        or service_account.get("project_id")
        != "smart-hajj-guardian-513417"
    ):
        raise RuntimeError(
            "Invalid Firebase service account configuration"
        )

    return firebase_admin.initialize_app(
        credentials.Certificate(service_account),
        name="smart-hajj-guardian",
    )


class FirebaseNotificationService:

    @staticmethod
    def send_to_token(
        token: str,
        title: str,
        body: str,
        notification_type: str,
        data: dict | None = None,
    ) -> str:
        """
        Send one push notification to an Android device.

        All FCM data payload values must be strings.
        """

        payload = {
            "type": notification_type,
            **{
                str(key): str(value)
                for key, value in (data or {}).items()
            },
        }

        message = messaging.Message(
            token=token,
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=payload,
            android=messaging.AndroidConfig(
                priority="high",
            ),
        )

        return messaging.send(
            message,
            app=get_firebase_app(),
        )


    @staticmethod
    def send_to_user(
        user_id: int,
        title: str,
        body: str,
        notification_type: str,
        data: dict | None = None,
    ) -> int:
        """Send a push to all active devices owned by a user."""

        with SessionLocal() as db:
            tokens = db.execute(
                text("""
                    SELECT fcm_token
                    FROM user_fcm_devices
                    WHERE user_id = :user_id
                      AND is_active = TRUE
                """),
                {"user_id": user_id},
            ).scalars().all()

        sent_count = 0

        for token in tokens:
            try:
                FirebaseNotificationService.send_to_token(
                    token=token,
                    title=title,
                    body=body,
                    notification_type=notification_type,
                    data=data,
                )
                sent_count += 1

            except messaging.UnregisteredError:
                with SessionLocal() as db:
                    db.execute(
                        text("""
                            UPDATE user_fcm_devices
                            SET is_active = FALSE,
                                updated_at = NOW()
                            WHERE fcm_token = :token
                        """),
                        {"token": token},
                    )
                    db.commit()

            except Exception:
                logger.exception(
                    "FCM notification failed for user_id=%s",
                    user_id,
                )

        return sent_count

    @staticmethod
    def notify_group_message(
        group_id: int,
        sender_user_id: int,
        message_id: int | None = None,
    ) -> int:
        """Notify active group members except the sender."""

        with SessionLocal() as db:
            recipients = db.execute(
                text("""
                    SELECT DISTINCT gm.user_id
                    FROM group_members gm
                    WHERE gm.group_id = :group_id
                      AND gm.user_id != :sender_user_id
                      AND gm.is_active = TRUE
                """),
                {
                    "group_id": group_id,
                    "sender_user_id": sender_user_id,
                },
            ).scalars().all()

        total_sent = 0

        for user_id in recipients:
            total_sent += FirebaseNotificationService.send_to_user(
                user_id=user_id,
                title="Smart Hajj Guardian",
                body="You have a new group message.",
                notification_type="NEW_MESSAGE",
                data={
                    "group_id": group_id,
                    "sender_user_id": sender_user_id,
                    **(
                        {"message_id": message_id}
                        if message_id is not None
                        else {}
                    ),
                },
            )

        return total_sent

    @staticmethod
    def notify_geofence_event(
        group_id: int,
        member_user_id: int,
        event_type: str,
        distance_m: float | None = None,
    ) -> int:
        """Notify the leader about an active group member."""

        event_bodies = {
            "GEOFENCE_EXITED": (
                "A group member has left the 500-metre safe zone."
            ),
            "GEOFENCE_OUTSIDE": (
                "A group member was detected outside the safe zone."
            ),
            "GEOFENCE_ENTERED": (
                "A group member has returned to the safe zone."
            ),
        }

        if event_type not in event_bodies:
            return 0

        with SessionLocal() as db:
            leader_user_id = db.execute(
                text("""
                    SELECT cg.leader_id
                    FROM chat_groups cg
                    JOIN group_members gm
                      ON gm.group_id = cg.id
                    WHERE cg.id = :group_id
                      AND gm.user_id = :member_user_id
                      AND gm.is_active = TRUE
                """),
                {
                    "group_id": group_id,
                    "member_user_id": member_user_id,
                },
            ).scalar_one_or_none()

        if leader_user_id is None:
            return 0

        if leader_user_id == member_user_id:
            return 0

        data = {
            "group_id": group_id,
            "member_user_id": member_user_id,
        }

        if distance_m is not None:
            data["distance_m"] = round(distance_m, 2)

        return FirebaseNotificationService.send_to_user(
            user_id=leader_user_id,
            title="Smart Hajj Guardian - Geofence Alert",
            body=event_bodies[event_type],
            notification_type=event_type,
            data=data,
        )

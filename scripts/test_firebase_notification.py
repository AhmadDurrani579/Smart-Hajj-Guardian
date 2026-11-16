
from unittest.mock import patch

from app.services.firebase_notification_service import (
    FirebaseNotificationService,
)


def main():
    fake_token = "TEST_FCM_TOKEN_BACKEND_ONLY_123456789"

    with patch(
        "app.services.firebase_notification_service.messaging.send",
        return_value="projects/smart-hajj-guardian-513417/messages/test123",
    ) as mock_send, patch(
        "app.services.firebase_notification_service.get_firebase_app"
    ):
        response = FirebaseNotificationService.send_to_token(
            token=fake_token,
            title="Smart Hajj Guardian",
            body="This is a test notification from FastAPI.",
            notification_type="TEST_NOTIFICATION",
            data={"user_id": 1, "group_id": 1},
        )

        mock_send.assert_called_once()

        message = mock_send.call_args.args[0]

        assert message.token == fake_token
        assert message.notification.title == "Smart Hajj Guardian"
        assert message.notification.body == (
            "This is a test notification from FastAPI."
        )
        assert message.data == {
            "type": "TEST_NOTIFICATION",
            "user_id": "1",
            "group_id": "1",
        }

        print("SUCCESS: Firebase notification function executed.")
        print("Notification type:", message.data["type"])
        print("Notification title:", message.notification.title)
        print("Notification body:", message.notification.body)
        print("Mock Firebase response:", response)
        print("Note: This test does not contact Firebase.")


if __name__ == "__main__":
    main()

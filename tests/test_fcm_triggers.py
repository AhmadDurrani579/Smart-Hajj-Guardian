
import asyncio
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.api.v1.endpoints import group_websocket as ws
from app.services.firebase_notification_service import (
    FirebaseNotificationService,
)


class TestFirebaseTriggers(unittest.TestCase):


    def test_chat_notification(self):
        """Verify SEND_MESSAGE triggers Firebase notification."""

        saved_message = MagicMock()
        saved_message.model_dump.return_value = {
            "id": 100,
            "group_id": 1,
            "sender_id": 6,
            "message": "Hello from User 6",
        }

        with (
            patch.object(
                ws,
                "authenticate_token",
                return_value=6,
            ),
            patch.object(
                ws,
                "check_membership",
                return_value=True,
            ),
            patch.object(
                ws.GroupMessageService,
                "send_message",
                return_value=saved_message,
            ),
            patch.object(
                FirebaseNotificationService,
                "notify_group_message",
                return_value=1,
            ) as mock_fcm,
        ):
            with TestClient(app) as client:
                with client.websocket_connect(
                    "/api/v1/ws/groups/1"
                ) as websocket:

                    # 1. Authenticate
                    websocket.send_json({
                        "type": "AUTH",
                        "token": "MOCK_TEST_JWT",
                    })

                    auth_response = websocket.receive_json()
                    print("Authentication:", auth_response)

                    self.assertEqual(
                        auth_response["type"],
                        "AUTH_SUCCESS",
                    )

                    # 2. Send chat message
                    websocket.send_json({
                        "type": "SEND_MESSAGE",
                        "data": {
                            "message_text": "Hello from User 6"
                        },
                    })

                    # 3. Receive message confirmation
                    message_response = websocket.receive_json()
                    print("Message response:", message_response)

                    self.assertEqual(
                        message_response["type"],
                        "MESSAGE_SAVED",
                        f"Unexpected response: {message_response}",
                    )

                    # 4. Receive broadcast, if delivered
                    broadcast_response = websocket.receive_json()
                    print("Broadcast:", broadcast_response)

                    self.assertEqual(
                        broadcast_response["type"],
                        "NEW_MESSAGE",
                    )

                    # 5. Verify Firebase was called.
                    # The notification runs after the broadcast;
                    # this receives the broadcast before the assertion.
                    mock_fcm.assert_called_once_with(
                        group_id=1,
                        sender_user_id=6,
                    )

        print("PASS: Chat notification trigger")


    def test_geofence_notification(self):
        """Check geofence event -> Firebase call."""

        sample_events = [
            {
                "type": "GEOFENCE_EXITED",
                "data": {
                    "group_id": 1,
                    "user_id": 6,
                    "leader_user_id": 1,
                    "distance_m": 667.17,
                    "radius_m": 500,
                    "state": "OUTSIDE",
                },
            },
        ]

        with (
            patch.object(
                ws,
                "evaluate_geofence_sync",
                return_value=(1, sample_events),
            ),
            patch.object(
                FirebaseNotificationService,
                "notify_geofence_event",
                return_value=1,
            ) as mock_fcm,
            patch.dict(
                ws.geofence_connections,
                {1: {}},
            ),
        ):
            asyncio.run(
                ws.evaluate_and_notify_geofence(
                    group_id=1,
                )
            )

            mock_fcm.assert_called_once_with(
                group_id=1,
                member_user_id=6,
                event_type="GEOFENCE_EXITED",
                distance_m=667.17,
            )

        print("PASS: Geofence notification trigger")


if __name__ == "__main__":
    unittest.main(verbosity=2)

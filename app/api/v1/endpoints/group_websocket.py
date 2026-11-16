
import asyncio
import json
import logging

import jwt

from fastapi import (
    APIRouter,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from pydantic import ValidationError

from app.core.config import get_settings
from app.db.session import SessionLocal

from app.schemas.group_message import (
    MessageHistoryRequest,
    MessageSendRequest,
)
from app.schemas.member_location import (
    LocationSharingRequest,
    LocationUpdateRequest,
)

from app.services.group_message_service import GroupMessageService
from app.services.member_location_service import MemberLocationService
from app.services.websocket_manager import websocket_manager
import logging
from starlette.concurrency import run_in_threadpool
from app.services.geofence_service import GeofenceService
import asyncio
from app.services.firebase_notification_service import FirebaseNotificationService

logger = logging.getLogger(__name__)
router = APIRouter()


def authenticate_token(token: str) -> int | None:
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "sub"]},
        )

        if payload.get("type") != "access":
            return None

        user_id = int(payload["sub"])
        return user_id if user_id > 0 else None

    except (
        jwt.InvalidTokenError,
        ValueError,
        TypeError,
        KeyError,
    ):
        return None


def check_membership(group_id: int, user_id: int) -> bool:
    with SessionLocal() as db:
        service = GroupMessageService(db)

        return (
            service.repository.get_active_membership(
                group_id=group_id,
                user_id=user_id,
            )
            is not None
        )


geofence_logger = logging.getLogger(__name__)

# Local authenticated WebSocket registry.
# Separate from the existing chat manager.
geofence_connections: dict[int, dict[WebSocket, int]] = {}


def register_geofence_connection(
    group_id: int,
    user_id: int,
    websocket: WebSocket,
) -> None:
    geofence_connections.setdefault(
        group_id, {}
    )[websocket] = user_id


def unregister_geofence_connection(
    group_id: int,
    websocket: WebSocket,
) -> None:
    group_connections = geofence_connections.get(
        group_id
    )

    if not group_connections:
        return

    group_connections.pop(websocket, None)

    if not group_connections:
        geofence_connections.pop(group_id, None)


def evaluate_geofence_sync(
    group_id: int,
) -> tuple[int, list[dict]]:
    # Database sessions are created inside the
    # worker thread that uses them.
    with SessionLocal() as db:
        return GeofenceService(db).evaluate_group(
            group_id
        )

def get_geofence_status_sync(
    group_id: int,
    user_id: int,
) -> dict:
    with SessionLocal() as db:
        return GeofenceService(db).get_group_distance_status(
            group_id=group_id,
            user_id=user_id,
        )



async def evaluate_and_notify_geofence(
    group_id: int,
) -> None:
    # 1. Evaluate the geofence using PostgreSQL
    try:
        leader_id, events = await run_in_threadpool(
            evaluate_geofence_sync,
            group_id,
        )
    except Exception:
        geofence_logger.exception(
            "Geofence evaluation failed for group %s",
            group_id,
        )
        return

    # No geofence transitions detected
    if not events or not leader_id:
        return

    # 2. Get active WebSocket connections
    sockets = list(
        geofence_connections.get(
            group_id, {}
        ).items()
    )

    # =========================================
    # WEBSOCKET GEOFENCE NOTIFICATIONS
    # =========================================

    for websocket, connected_user_id in sockets:

        # Only notify the group leader
        if connected_user_id != leader_id:
            continue

        # Verify the leader is still a group member
        if not await run_in_threadpool(
            check_membership,
            group_id,
            connected_user_id,
        ):
            continue

        for event in events:
            try:
                await websocket.send_json(event)
            except Exception:
                geofence_logger.warning(
                    "Could not deliver geofence alert "
                    "to leader of group %s",
                    group_id,
                )
                break

    # =========================================
    # FIREBASE GEOFENCE PUSH NOTIFICATIONS
    # =========================================

    # Runs independently of WebSocket connections
    for event in events:
        try:
            await asyncio.to_thread(
                FirebaseNotificationService.notify_geofence_event,
                group_id=group_id,
                member_user_id=event["data"]["user_id"],
                event_type=event["type"],
                distance_m=event["data"].get("distance_m"),
            )

        except Exception:
            geofence_logger.exception(
                "Failed to send Firebase geofence "
                "notification for group %s",
                group_id,
            )

        
        
@router.websocket("/groups/{group_id}")
async def group_chat_websocket(
    websocket: WebSocket,
    group_id: int,
):
    await websocket.accept()

    authenticated = False

    try:
        # Authenticate immediately after connection.
        raw_auth = await asyncio.wait_for(
            websocket.receive_text(),
            timeout=10,
        )

        try:
            auth_event = json.loads(raw_auth)
        except json.JSONDecodeError:
            await websocket.close(
                code=1008,
                reason="Invalid authentication",
            )
            return

        if (
            not isinstance(auth_event, dict)
            or auth_event.get("type") != "AUTH"
        ):
            await websocket.close(
                code=1008,
                reason="Authentication required",
            )
            return

        token = auth_event.get("token")

        if not isinstance(token, str):
            await websocket.close(
                code=1008,
                reason="Invalid token",
            )
            return

        user_id = authenticate_token(token)

        if user_id is None:
            await websocket.close(
                code=1008,
                reason="Invalid access token",
            )
            return

        if not check_membership(group_id, user_id):
            await websocket.close(
                code=1008,
                reason="Not a group member",
            )
            return

        await websocket_manager.connect(
            group_id,
            websocket,
        )
        authenticated = True
        register_geofence_connection(
            group_id=group_id,
            user_id=user_id,
            websocket=websocket,
        )
        await websocket.send_json({
            "type": "AUTH_SUCCESS",
            "data": {
                "group_id": group_id,
                "user_id": user_id,
            },
        })

        while True:
            raw_message = await websocket.receive_text()

            try:
                event = json.loads(raw_message)

                if not isinstance(event, dict):
                    raise ValueError(
                        "Event must be an object"
                    )

                event_type = event.get("type")
                data = event.get("data", {})

                if not isinstance(data, dict):
                    raise ValueError(
                        "Data must be an object"
                    )

                if authenticate_token(token) != user_id:
                    await websocket.close(
                        code=1008,
                        reason="Access token expired or invalid",
                    )
                    break

                if not check_membership(group_id, user_id):
                    await websocket.close(
                        code=1008,
                        reason="Group membership no longer active",
                    )
                    break

                # ===================================
                # EXISTING GROUP CHAT
                # ===================================

                if event_type == "SEND_MESSAGE":
                    request = MessageSendRequest.model_validate(
                        data
                    )

                    with SessionLocal() as db:
                        service = GroupMessageService(db)

                        saved = service.send_message(
                            group_id=group_id,
                            user_id=user_id,
                            data=request,
                        )

                    message_data = saved.model_dump(
                        mode="json"
                    )

                    await websocket.send_json({
                        "type": "MESSAGE_SAVED",
                        "data": message_data,
                    })

                    await websocket_manager.broadcast(
                        group_id,
                        {
                            "type": "NEW_MESSAGE",
                            "data": message_data,
                        },
                    )

                    # Send Firebase notification to other group members
                    await asyncio.to_thread(
                        FirebaseNotificationService.notify_group_message,
                        group_id=group_id,
                        sender_user_id=user_id,
                    )

                elif event_type == "GET_HISTORY":
                    request = MessageHistoryRequest.model_validate(
                        data
                    )

                    with SessionLocal() as db:
                        service = GroupMessageService(db)

                        messages = service.get_history(
                            group_id=group_id,
                            user_id=user_id,
                            data=request,
                        )

                    await websocket.send_json({
                        "type": "MESSAGE_HISTORY",
                        "data": [
                            message.model_dump(
                                mode="json"
                            )
                            for message in messages
                        ],
                    })

                # ===================================
                # GPS: ENABLE / DISABLE SHARING
                # ===================================

                elif event_type == "SET_LOCATION_SHARING":
                    request = LocationSharingRequest.model_validate(
                        data
                    )

                    with SessionLocal() as db:
                        service = MemberLocationService(db)

                        result = service.update_sharing(
                            user_id=user_id,
                            group_id=group_id,
                            data=request,
                        )

                    sharing_data = result.model_dump(
                        mode="json"
                    )

                    await websocket.send_json({
                        "type": "LOCATION_SHARING_UPDATED",
                        "data": sharing_data,
                    })
                    await evaluate_and_notify_geofence(
                        group_id=group_id,
                    )
                    if not request.enabled:
                        await websocket_manager.broadcast(
                            group_id,
                            {
                                "type": "LOCATION_REMOVED",
                                "data": {
                                    "group_id": group_id,
                                    "user_id": user_id,
                                },
                            },
                        )

                # ===================================
                # GPS: SAVE NEW LOCATION
                # ===================================

                
                elif event_type == "SEND_LOCATION":
                    request = LocationUpdateRequest.model_validate(data)

                    # 1. Save GPS location in Neon
                    with SessionLocal() as db:
                        service = MemberLocationService(db)

                        result = service.update_location(
                            user_id=user_id,
                            group_id=group_id,
                            data=request,
                        )

                    location_data = result.model_dump(mode="json")

                    # 2. Confirm GPS location was saved
                    await websocket.send_json({
                        "type": "LOCATION_SAVED",
                        "data": location_data,
                    })

                    # 3. Evaluate 500-metre geofence
                    await evaluate_and_notify_geofence(
                        group_id=group_id,
                    )

                    # 4. Return distances and geofence status
                    geofence_status = await run_in_threadpool(
                        get_geofence_status_sync,
                        group_id,
                        user_id,
                    )

                    await websocket.send_json({
                        "type": "GEOFENCE_STATUS",
                        "data": geofence_status,
                    })

                    # 5. Broadcast updated GPS coordinates
                    await websocket_manager.broadcast(
                        group_id,
                        {
                            "type": "LOCATION_UPDATED",
                            "data": location_data,
                        },
                    )


                elif event_type == "GET_GEOFENCE_STATUS":
                    if data:
                        raise ValueError(
                            "GET_GEOFENCE_STATUS does not accept data"
                        )

                    result = await run_in_threadpool(
                        get_geofence_status_sync,
                        group_id,
                        user_id,
                    )

                    await websocket.send_json({
                        "type": "GEOFENCE_STATUS",
                        "data": result,
                    })
                
                # ===================================
                # GPS: GET GROUP LOCATIONS
                # ===================================

                elif event_type == "GET_GROUP_LOCATIONS":
                    if data:
                        raise ValueError(
                            "GET_GROUP_LOCATIONS does not accept data"
                        )

                    with SessionLocal() as db:
                        service = MemberLocationService(db)

                        result = service.get_group_locations(
                            user_id=user_id,
                            group_id=group_id,
                        )

                    await websocket.send_json({
                        "type": "GROUP_LOCATIONS",
                        "data": result.model_dump(
                            mode="json"
                        ),
                    })

                else:
                    await websocket.send_json({
                        "type": "ERROR",
                        "detail": "Unknown event type",
                    })

            except (ValidationError, ValueError, json.JSONDecodeError) as exc:
                    await websocket.send_json({
                        "type": "ERROR",
                        "detail": str(exc),
                    })

            except HTTPException as exc:
                    await websocket.send_json({
                        "type": "ERROR",
                        "detail": exc.detail,
                    })

                # Geofence authorization error
            except PermissionError:
                    await websocket.send_json({
                        "type": "ERROR",
                        "detail": "Not authorized for this group",
                    })

            except Exception:
                    logger.exception("Group WebSocket event failed")

                    await websocket.send_json({
                        "type": "ERROR",
                        "detail": "Unable to process request",
                    })


            

    except asyncio.TimeoutError:
        await websocket.close(
            code=1008,
            reason="Authentication timeout",
        )

    except (WebSocketDisconnect, RuntimeError):
        pass

    finally:
        if authenticated:
            unregister_geofence_connection(
                group_id,
                websocket,
            )

            await websocket_manager.disconnect(
                group_id,
                websocket,
            )
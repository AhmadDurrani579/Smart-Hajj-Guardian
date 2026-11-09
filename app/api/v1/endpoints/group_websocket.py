
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
                    request = LocationUpdateRequest.model_validate(
                        data
                    )

                    with SessionLocal() as db:
                        service = MemberLocationService(db)

                        result = service.update_location(
                            user_id=user_id,
                            group_id=group_id,
                            data=request,
                        )

                    location_data = result.model_dump(
                        mode="json"
                    )

                    await websocket.send_json({
                        "type": "LOCATION_SAVED",
                        "data": location_data,
                    })

                    await websocket_manager.broadcast(
                        group_id,
                        {
                            "type": "LOCATION_UPDATED",
                            "data": location_data,
                        },
                    )

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

            except (
                ValidationError,
                ValueError,
                json.JSONDecodeError,
            ) as exc:
                await websocket.send_json({
                    "type": "ERROR",
                    "detail": str(exc),
                })

            except HTTPException as exc:
                await websocket.send_json({
                    "type": "ERROR",
                    "detail": exc.detail,
                })

            except Exception:
                logger.exception(
                    "Group WebSocket event failed"
                )

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
            await websocket_manager.disconnect(
                group_id,
                websocket,
            )

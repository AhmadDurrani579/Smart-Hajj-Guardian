
from fastapi import FastAPI

from app.core.config import get_settings
from app.api.v1.router import api_router
from app.api.v1.endpoints.group_websocket import group_chat_websocket


settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description="Hajj/Umrah Guidance and Private Group Safety API",
    version="1.0.0",
    debug=settings.DEBUG,
)

# Existing REST APIs
app.include_router(
    api_router,
    prefix="/api/v1",
)

# Group Chat WebSocket
app.add_api_websocket_route(
    "/api/v1/ws/groups/{group_id}",
    group_chat_websocket,
)


@app.get("/")
def root():
    return {
        "message": f"{settings.APP_NAME} API is running",
        "environment": settings.ENVIRONMENT,
    }

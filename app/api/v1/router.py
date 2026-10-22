
from fastapi import APIRouter
from app.api.v1.endpoints import groups
from app.api.v1.endpoints import (
    auth,
    health,
    users,
    journeys,
    guidance,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(journeys.router)
api_router.include_router(guidance.router)
api_router.include_router(
    groups.router,
    prefix="/groups",
    tags=["Groups"],
)
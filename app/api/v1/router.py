from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    health,
    users,
    journeys,
    guidance,
    groups,
    dashboard,
)

api_router = APIRouter()

# Existing routes
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

# Dashboard
api_router.include_router(dashboard.router)
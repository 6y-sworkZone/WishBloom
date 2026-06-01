from api.v1.endpoints.auth import router as auth_router
from api.v1.endpoints.calendar import router as calendar_router
from api.v1.endpoints.achievements import router as achievements_router
from api.v1.endpoints.wishes import router as wishes_router
from api.v1.endpoints.interactions import router as interactions_router
from api.v1.endpoints.community import router as community_router
from api.v1.endpoints.tree import router as tree_router
from api.v1.endpoints.privacy import router as privacy_router

__all__ = ["auth_router", "calendar_router", "achievements_router", "wishes_router", "interactions_router", "community_router", "tree_router", "privacy_router"]

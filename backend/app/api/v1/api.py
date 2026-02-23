from fastapi import APIRouter
from app.api.v1.endpoints import library, settings, store, admin, auth, playtime, setup, reviews, profiles, community, friends, news

api_router = APIRouter()

api_router.include_router(setup.router, prefix="/setup", tags=["setup"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(library.router, prefix="/library", tags=["library"])
api_router.include_router(playtime.router, prefix="/playtime", tags=["playtime"])
api_router.include_router(reviews.router, prefix="/reviews", tags=["reviews"])
api_router.include_router(profiles.router, prefix="/profiles", tags=["profiles"])
api_router.include_router(community.router, prefix="/community", tags=["community"])
api_router.include_router(friends.router, prefix="/friends", tags=["friends"])
api_router.include_router(news.router, prefix="/news", tags=["news"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(store.router, prefix="/store", tags=["store"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])

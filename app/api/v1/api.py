from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.user.router import router as user_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(user_router, prefix="/users", tags=["users"])

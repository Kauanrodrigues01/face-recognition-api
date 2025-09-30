from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.modules.auth.router import get_current_superuser
from app.modules.auth.service import AuthService
from app.modules.user.schemas import User, UserCreate, UserUpdate
from app.modules.user.service import UserService

router = APIRouter()


def get_user_service(
    db: AsyncSession = Depends(get_db),
) -> UserService:
    return UserService(db)


def get_auth_service() -> AuthService:
    return AuthService()


@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(
    user: UserCreate,
    user_service: UserService = Depends(get_user_service),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Create a new user"""
    # Check if user already exists
    db_user = await user_service.get_by_email(email=user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    hashed_password = auth_service.get_password_hash(user.password)
    return await user_service.create(user, hashed_password)


@router.get("/", response_model=list[User])
async def read_users(
    current_user: Annotated[User, Depends(get_current_superuser)],
    skip: int = 0,
    limit: int = 100,
    user_service: UserService = Depends(get_user_service),
):
    """Get all users - Admin only"""
    return await user_service.get_all(skip=skip, limit=limit)


@router.get("/{user_id}", response_model=User)
async def read_user(
    user_id: int,
    current_user: Annotated[User, Depends(get_current_superuser)],
    user_service: UserService = Depends(get_user_service),
):
    """Get a specific user by ID - Admin only"""
    user = await user_service.get_by_id(user_id=user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


@router.put("/{user_id}", response_model=User)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: Annotated[User, Depends(get_current_superuser)],
    user_service: UserService = Depends(get_user_service),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Update a user - Admin only"""
    hashed_password = None
    if user_update.password:
        hashed_password = auth_service.get_password_hash(user_update.password)

    user = await user_service.update(
        user_id=user_id, user_data=user_update, hashed_password=hashed_password
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: Annotated[User, Depends(get_current_superuser)],
    user_service: UserService = Depends(get_user_service),
):
    """Delete a user - Admin only"""
    success = await user_service.delete(user_id=user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return None

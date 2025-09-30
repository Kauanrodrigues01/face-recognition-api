from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.user.models import User
from app.modules.user.schemas import UserCreate, UserUpdate


class UserService:
    """Service for User business logic"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Get a user by ID"""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by email"""
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get all users with pagination"""
        result = await self.db.execute(select(User).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def create(self, user_data: UserCreate, hashed_password: str) -> User:
        """Create a new user"""
        db_user = User(
            email=user_data.email,
            name=user_data.name,
            hashed_password=hashed_password,
        )
        self.db.add(db_user)
        await self.db.flush()
        await self.db.refresh(db_user)
        return db_user

    async def update(
        self, user_id: int, user_data: UserUpdate, hashed_password: Optional[str] = None
    ) -> Optional[User]:
        """Update a user"""
        db_user = await self.get_by_id(user_id)
        if not db_user:
            return None

        update_data = user_data.model_dump(exclude_unset=True)

        # Remove password from update_data, use hashed_password if provided
        if "password" in update_data:
            del update_data["password"]

        if hashed_password:
            update_data["hashed_password"] = hashed_password

        for field, value in update_data.items():
            setattr(db_user, field, value)

        await self.db.flush()
        await self.db.refresh(db_user)
        return db_user

    async def delete(self, user_id: int) -> bool:
        """Delete a user"""
        db_user = await self.get_by_id(user_id)
        if not db_user:
            return False

        await self.db.delete(db_user)
        await self.db.flush()
        return True

    async def authenticate(self, email: str, verify_password_func) -> Optional[User]:
        """Authenticate a user"""
        user = await self.get_by_email(email)
        if not user:
            return None
        return user

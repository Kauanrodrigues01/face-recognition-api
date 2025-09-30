from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    email: EmailStr
    name: str


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    name: str | None = None
    password: str | None = None
    is_active: bool | None = None


class UserInDBBase(BaseModel):
    id: int
    email: EmailStr
    name: str
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class User(UserInDBBase):
    face_enrolled: bool = False
    face_enrollment_quality: int | None = None


class UserInDB(UserInDBBase):
    hashed_password: str
    face_embedding_encrypted: str | None = None
    face_enrollment_id: str | None = None
    face_enrolled: bool = False
    face_enrollment_quality: int | None = None

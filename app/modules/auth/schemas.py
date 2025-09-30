from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: str | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class FaceEnrollRequest(BaseModel):
    """Schema for face enrollment - register facial biometric"""

    face_image_base64: str


class FaceEnrollResponse(BaseModel):
    """Response for face enrollment"""

    success: bool
    message: str
    quality_score: int
    face_enrolled: bool


class FaceLoginRequest(BaseModel):
    """Schema for face login - authenticate with email + face"""

    email: EmailStr
    face_image_base64: str


class FaceLoginResponse(BaseModel):
    """Response for face login"""

    access_token: str
    token_type: str
    user: dict

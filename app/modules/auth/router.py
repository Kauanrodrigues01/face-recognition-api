import base64
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.database import get_db
from app.modules.auth.schemas import (
    FaceEnrollResponse,
    FaceLoginResponse,
    FaceTestResponse,
    Token,
    UserLogin,
)
from app.modules.auth.service import AuthService
from app.modules.user.schemas import User
from app.modules.user.service import UserService
from app.services.encryption_service import (
    EncryptionService,
    get_encryption_service,
)
from app.services.face_recognition_service import (
    FaceRecognitionService,
    LowQualityFaceError,
    MultipleFacesError,
    NoFaceDetectedError,
    SpoofingDetectedError,
    get_face_recognition_service,
)

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token")


def get_auth_service() -> AuthService:
    return AuthService()


def get_face_service() -> FaceRecognitionService:
    return get_face_recognition_service()


def get_encryption_service_instance() -> EncryptionService:
    return get_encryption_service(settings.FACE_ENCRYPTION_KEY)


def get_user_service(
    db: AsyncSession = Depends(get_db),
    face_service: FaceRecognitionService = Depends(get_face_service),
    encryption_service: EncryptionService = Depends(get_encryption_service_instance),
) -> UserService:
    return UserService(db, face_service, encryption_service)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    user_service: UserService = Depends(get_user_service),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    """Get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    email = auth_service.decode_access_token(token)
    if email is None:
        raise credentials_exception

    user = await user_service.get_by_email(email=email)
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_superuser(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """Get current superuser"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Administrator access required.",
        )
    return current_user


@router.post("/token", response_model=Token)
async def login_for_swagger(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    user_service: UserService = Depends(get_user_service),
    auth_service: AuthService = Depends(get_auth_service),
):
    """OAuth2 compatible token endpoint for Swagger UI authentication"""
    user = await user_service.get_by_email(email=form_data.username)
    if not user or not auth_service.verify_password(
        form_data.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login", response_model=Token)
async def login(
    user_login: UserLogin,
    user_service: UserService = Depends(get_user_service),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Login endpoint with JSON body - returns JWT token"""
    user = await user_service.get_by_email(email=user_login.email)
    if not user or not auth_service.verify_password(
        user_login.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=User)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Get current user info"""
    return current_user


@router.post("/face/enroll", response_model=FaceEnrollResponse)
async def enroll_face(
    current_user: Annotated[User, Depends(get_current_active_user)],
    user_service: UserService = Depends(get_user_service),
    face_image_base64: str | None = Form(None),
    face_image_file: UploadFile | None = File(None),
):
    """
    Enroll face biometric for current authenticated user.

    Requires JWT authentication.

    You can provide the face image in two ways:
    - face_image_base64: Base64 encoded image string
    - face_image_file: Upload image file directly

    Only one method should be provided.
    """
    # Validate that exactly one method is provided
    if not face_image_base64 and not face_image_file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either face_image_base64 or face_image_file must be provided",
        )

    if face_image_base64 and face_image_file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide only one: face_image_base64 or face_image_file",
        )

    # Convert file to base64 if file was provided
    if face_image_file:
        contents = await face_image_file.read()
        face_image_base64 = base64.b64encode(contents).decode("utf-8")

    try:
        result = await user_service.enroll_face(
            user_id=current_user.id,
            face_image_base64=face_image_base64,
        )

        return FaceEnrollResponse(
            success=result["success"],
            message=result["message"],
            quality_score=result["quality_score"],
            face_enrolled=True,
        )

    except NoFaceDetectedError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No face detected: {str(e)}",
        )
    except MultipleFacesError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Multiple faces detected: {str(e)}",
        )
    except LowQualityFaceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Face quality too low: {str(e)}",
        )
    except SpoofingDetectedError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Potential spoofing detected: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Face enrollment failed: {str(e)}",
        )


@router.post("/face/login", response_model=FaceLoginResponse)
async def face_login(
    user_service: UserService = Depends(get_user_service),
    auth_service: AuthService = Depends(get_auth_service),
    email: str = Form(...),
    face_image_base64: str | None = Form(None),
    face_image_file: UploadFile | None = File(None),
):
    """
    Login with email + face biometric.

    Returns JWT token if authentication successful.
    Uses HIGH security level for face matching.

    You can provide the face image in two ways:
    - face_image_base64: Base64 encoded image string
    - face_image_file: Upload image file directly

    Only one method should be provided.
    """
    # Validate that exactly one method is provided
    if not face_image_base64 and not face_image_file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either face_image_base64 or face_image_file must be provided",
        )

    if face_image_base64 and face_image_file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide only one: face_image_base64 or face_image_file",
        )

    # Convert file to base64 if file was provided
    if face_image_file:
        contents = await face_image_file.read()
        face_image_base64 = base64.b64encode(contents).decode("utf-8")

    try:
        # Get user to verify face enrollment
        user = await user_service.get_by_email(email=email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.face_enrolled:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Face biometric not enrolled for this user",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Verify face and get confidence score
        verification_result = await user_service.verify_face(
            user_id=user.id,
            face_image_base64=face_image_base64,
        )

        confidence_percent = verification_result["confidence"]
        MIN_CONFIDENCE_THRESHOLD = 80.0

        # Check if verified and meets minimum confidence
        if not verification_result["verified"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Face authentication failed. Confidence: {confidence_percent:.1f}%. Minimum required: {MIN_CONFIDENCE_THRESHOLD}%",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if confidence_percent < MIN_CONFIDENCE_THRESHOLD:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Confidence too low: {confidence_percent:.1f}%. Minimum required: {MIN_CONFIDENCE_THRESHOLD}%",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Generate access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = auth_service.create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )

        return FaceLoginResponse(
            access_token=access_token,
            token_type="bearer",
            user={
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "face_enrolled": user.face_enrolled,
                "is_superuser": user.is_superuser,
                "is_active": user.is_active,
            },
        )

    except HTTPException:
        raise
    except (
        NoFaceDetectedError,
        MultipleFacesError,
        LowQualityFaceError,
        SpoofingDetectedError,
    ) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Face verification failed: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Face login failed: {str(e)}",
        )


@router.post("/face/test", response_model=FaceTestResponse)
async def test_face_recognition(
    current_user: Annotated[User, Depends(get_current_active_user)],
    email: str = Form(...),  # noqa: PT028
    user_service: UserService = Depends(get_user_service),  # noqa: PT028
    face_image_base64: str | None = Form(None),  # noqa: PT028
    face_image_file: UploadFile | None = File(None),  # noqa: PT028
):
    """
    Test face recognition without logging in.

    Requires authentication (user must be logged in).
    Tests if the provided face matches the enrolled face for the given email.
    Returns match result and confidence score.
    """
    # Validate that exactly one method is provided
    if not face_image_base64 and not face_image_file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either face_image_base64 or face_image_file must be provided",
        )

    if face_image_base64 and face_image_file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide only one: face_image_base64 or face_image_file",
        )

    # Convert file to base64 if file was provided
    if face_image_file:
        contents = await face_image_file.read()
        face_image_base64 = base64.b64encode(contents).decode("utf-8")

    try:
        # Get target user
        target_user = await user_service.get_by_email(email=email)
        if not target_user:
            return FaceTestResponse(
                match=False,
                confidence=0.0,
                message="User not found",
                user=None,
            )

        if not target_user.face_enrolled:
            return FaceTestResponse(
                match=False,
                confidence=0.0,
                message="User has not enrolled face biometrics",
                user=None,
            )

        # Test face recognition and get actual confidence score
        try:
            verification_result = await user_service.verify_face(
                user_id=target_user.id,
                face_image_base64=face_image_base64,
            )

            # Convert confidence from 0-100 to 0-1 for frontend
            confidence_normalized = verification_result["confidence"] / 100.0

            if verification_result["verified"]:
                return FaceTestResponse(
                    match=True,
                    confidence=confidence_normalized,
                    message="Face recognized successfully",
                    user={
                        "id": target_user.id,
                        "email": target_user.email,
                        "name": target_user.name,
                        "face_enrolled": target_user.face_enrolled,
                    },
                )
            else:
                return FaceTestResponse(
                    match=False,
                    confidence=confidence_normalized,
                    message="Face does not match enrolled biometrics",
                    user=None,
                )
        except (
            NoFaceDetectedError,
            MultipleFacesError,
            LowQualityFaceError,
            SpoofingDetectedError,
        ) as e:
            return FaceTestResponse(
                match=False,
                confidence=0.0,
                message=f"Face verification failed: {str(e)}",
                user=None,
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Face test failed: {str(e)}",
        )

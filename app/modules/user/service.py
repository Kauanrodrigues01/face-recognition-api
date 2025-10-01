import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.user.models import User
from app.modules.user.schemas import UserCreate, UserUpdate
from app.services.encryption_service import EncryptionService
from app.services.face_recognition_service import (
    FaceQuality,
    FaceRecognitionService,
    LowQualityFaceError,
    MultipleFacesError,
    NoFaceDetectedError,
    SecurityLevel,
    SpoofingDetectedError,
)


class UserService:
    """Service for User business logic"""

    def __init__(
        self,
        db: AsyncSession,
        face_service: FaceRecognitionService | None = None,
        encryption_service: EncryptionService | None = None,
    ):
        self.db = db
        self.face_service = face_service
        self.encryption_service = encryption_service

    async def get_by_id(self, user_id: int) -> User | None:
        """Get a user by ID"""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Get a user by email"""
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Get all users with pagination"""
        result = await self.db.execute(select(User).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def create(self, user_data: UserCreate, hashed_password: str) -> User:
        """Create a new user"""
        db_user = User(
            email=user_data.email,
            name=user_data.name,
            hashed_password=hashed_password,
            is_superuser=user_data.is_superuser,
        )
        self.db.add(db_user)
        await self.db.flush()
        await self.db.refresh(db_user)
        return db_user

    async def update(
        self, user_id: int, user_data: UserUpdate, hashed_password: str | None = None
    ) -> User | None:
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

    async def authenticate(self, email: str) -> User | None:
        """Authenticate a user"""
        user = await self.get_by_email(email)
        if not user:
            return None
        return user

    async def enroll_face(
        self,
        user_id: int,
        face_image_base64: str,
        min_quality: FaceQuality = FaceQuality.ACCEPTABLE,
    ) -> dict:
        """
        Enroll face biometric for a user.

        Args:
            user_id: User ID
            face_image_base64: Face image as base64 string
            min_quality: Minimum required quality

        Returns:
            Dictionary with enrollment results

        Raises:
            ValueError: If services not configured
            NoFaceDetectedError, LowQualityFaceError, etc.
        """
        if not self.face_service or not self.encryption_service:
            raise ValueError("Face recognition services not configured")

        # Get user
        user = await self.get_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Detect and extract face embedding
        detection_result = self.face_service.detect_face(
            face_image_base64,
            min_quality=min_quality,
            check_liveness=True,
            allow_multiple_faces=False,
        )

        embedding = detection_result["embedding"]
        quality_score = detection_result["quality_score"]

        # Encrypt embedding
        encrypted_embedding = self.encryption_service.encrypt_embedding(embedding)

        # Generate enrollment ID
        enrollment_id = str(uuid.uuid4())

        # Update user record
        user.face_embedding_encrypted = encrypted_embedding
        user.face_enrollment_id = enrollment_id
        user.face_enrolled = True
        user.face_enrollment_quality = quality_score

        await self.db.flush()
        await self.db.refresh(user)

        return {
            "success": True,
            "message": "Face enrolled successfully",
            "quality_score": quality_score,
            "enrollment_id": enrollment_id,
            "detection_confidence": detection_result["detection_confidence"],
            "liveness": detection_result["liveness"],
        }

    async def verify_face(
        self,
        user_id: int,
        face_image_base64: str,
        security_level: SecurityLevel = SecurityLevel.VERY_HIGH,
        min_quality: FaceQuality = FaceQuality.ACCEPTABLE,
    ) -> dict:
        """
        Verify face against enrolled biometric.

        Args:
            user_id: User ID
            face_image_base64: Face image as base64 string
            security_level: Security level for matching
            min_quality: Minimum required quality

        Returns:
            Dictionary with verification results

        Raises:
            ValueError: If services not configured or face not enrolled
        """
        if not self.face_service or not self.encryption_service:
            raise ValueError("Face recognition services not configured")

        # Get user
        user = await self.get_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        if not user.face_enrolled or not user.face_embedding_encrypted:
            raise ValueError("User has not enrolled face biometric")

        # Decrypt stored embedding
        stored_embedding = self.encryption_service.decrypt_embedding(
            user.face_embedding_encrypted
        )

        # Verify face
        verification_result = self.face_service.verify_face(
            face_image_base64,
            stored_embedding,
            security_level=security_level,
            min_quality=min_quality,
            check_liveness=True,
        )

        return verification_result

    async def authenticate_with_face(
        self,
        email: str,
        face_image_base64: str,
        security_level: SecurityLevel = SecurityLevel.VERY_HIGH,
    ) -> User | None:
        """
        Authenticate user with email + face biometric.

        Args:
            email: User email
            face_image_base64: Face image as base64 string
            security_level: Security level for matching

        Returns:
            User if authenticated, None otherwise
        """
        if not self.face_service or not self.encryption_service:
            raise ValueError("Face recognition services not configured")

        # Get user by email
        user = await self.get_by_email(email)
        if not user:
            return None

        if not user.face_enrolled or not user.face_embedding_encrypted:
            return None

        try:
            # Verify face
            verification = await self.verify_face(
                user.id,
                face_image_base64,
                security_level=security_level,
                min_quality=FaceQuality.ACCEPTABLE,
            )

            if verification["verified"]:
                return user
            else:
                return None

        except (
            NoFaceDetectedError,
            MultipleFacesError,
            LowQualityFaceError,
            SpoofingDetectedError,
        ):
            return None

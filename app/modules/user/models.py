from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)

    # Biometric fields for facial recognition
    face_embedding_encrypted = Column(Text, nullable=True)  # Encrypted face embedding
    face_enrollment_id = Column(
        String, nullable=True
    )  # Enrollment ID from face service
    face_enrolled = Column(Boolean, default=False)  # Whether face is enrolled
    face_enrollment_quality = Column(
        Integer, nullable=True
    )  # Face quality score (0-100)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

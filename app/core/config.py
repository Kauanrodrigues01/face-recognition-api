from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="./.env", env_file_encoding="utf-8", extra="ignore"
    )

    # Project
    PROJECT_NAME: str = "Face Recognition API"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = "API for face recognition with PostgreSQL backend"
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:password@localhost:5432/face_recognition"
    )

    DATABASE_TEST_URL: str = (
        "postgresql+asyncpg://postgres:password@localhost:5433/face_recognition_test"
    )

    # CORS
    BACKEND_CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000"

    @property
    def cors_origins(self) -> list[str]:
        return [i.strip() for i in self.BACKEND_CORS_ORIGINS.split(",")]

    # Security
    SECRET_KEY: str = "your-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Face Recognition Encryption
    FACE_ENCRYPTION_KEY: str = "your-encryption-key-here"  # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"


settings = Settings()

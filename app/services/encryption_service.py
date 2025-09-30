"""
Encryption Service for Face Embeddings

Provides secure encryption/decryption for storing face embeddings in database.
Uses Fernet (symmetric encryption) from cryptography library.
"""

import base64
import json
from typing import List

from cryptography.fernet import Fernet


class EncryptionService:
    """Service for encrypting and decrypting face embeddings."""

    def __init__(self, encryption_key: str):
        """
        Initialize encryption service.

        Args:
            encryption_key: Base64-encoded Fernet key (32 bytes)
        """
        self.cipher = Fernet(encryption_key.encode())

    def encrypt_embedding(self, embedding: List[float]) -> str:
        """
        Encrypt face embedding for storage.

        Args:
            embedding: Face embedding as list of floats

        Returns:
            Encrypted embedding as base64 string
        """
        # Convert embedding to JSON string
        embedding_json = json.dumps(embedding)

        # Encrypt
        encrypted = self.cipher.encrypt(embedding_json.encode())

        # Return as base64 string for storage
        return base64.b64encode(encrypted).decode()

    def decrypt_embedding(self, encrypted_embedding: str) -> List[float]:
        """
        Decrypt face embedding from storage.

        Args:
            encrypted_embedding: Encrypted embedding as base64 string

        Returns:
            Face embedding as list of floats
        """
        # Decode from base64
        encrypted = base64.b64decode(encrypted_embedding.encode())

        # Decrypt
        decrypted = self.cipher.decrypt(encrypted)

        # Parse JSON and return
        return json.loads(decrypted.decode())

    @staticmethod
    def generate_key() -> str:
        """
        Generate a new Fernet encryption key.

        Returns:
            Base64-encoded key as string

        Note:
            Store this key securely in environment variables.
            If lost, encrypted embeddings cannot be recovered.
        """
        return Fernet.generate_key().decode()


# Singleton instance
_encryption_service: EncryptionService | None = None


def get_encryption_service(encryption_key: str) -> EncryptionService:
    """
    Get or create encryption service instance.

    Args:
        encryption_key: Encryption key from config

    Returns:
        EncryptionService instance
    """
    global _encryption_service

    if _encryption_service is None:
        _encryption_service = EncryptionService(encryption_key)

    return _encryption_service

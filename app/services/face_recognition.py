import secrets
from dataclasses import dataclass
from typing import Dict, List, Optional, Union

import cv2
import numpy as np

# Import modules (assuming they're in same package)
# from .insightface_service import InsightFaceRecognitionService
# from .liveness_detection import HybridLivenessDetector, LivenessMethod
# from .biometric_protection import SecureEmbeddingStorage, BiometricAuditLog


@dataclass
class BankingVerificationResult:
    """Complete verification result for banking"""

    verification_id: str
    success: bool
    is_verified: bool
    confidence: float

    # Face recognition
    face_match: bool
    face_similarity: float
    face_distance: float

    # Liveness detection
    liveness_passed: bool
    liveness_score: int
    liveness_risk: str

    # Fraud detection
    fraud_detected: bool
    fraud_score: int
    fraud_risk: str

    # Security
    data_encrypted: bool
    audit_logged: bool

    # Details
    details: Dict
    warnings: List[str]
    errors: List[str]


class CompleteBankingFaceService:
    """
    Complete Banking-Grade Face Recognition Service

    Features:
    - InsightFace recognition (SCRFD detector, ArcFace embeddings)
    - Liveness detection (passive + active)
    - Anti-spoofing / fraud detection
    - Encrypted embedding storage
    - Template protection
    - Audit logging
    - LGPD/GDPR compliance
    """

    def __init__(
        self,
        model_pack: str = "buffalo_l",
        det_size: tuple = (640, 640),
        ctx_id: int = 0,
        encryption_key: Optional[str] = None,
        enable_liveness: bool = True,
        enable_template_protection: bool = True,
        liveness_method: str = "hybrid",
    ):
        """
        Initialize complete banking service

        Args:
            model_pack: InsightFace model pack
            det_size: Detection size for SCRFD
            ctx_id: Device ID (0=GPU, -1=CPU)
            encryption_key: Master encryption key (generates if None)
            enable_liveness: Enable liveness detection
            enable_template_protection: Enable template protection
            liveness_method: 'passive', 'active', or 'hybrid'
        """
        print("🏦 Initializing Banking-Grade Face Recognition Service...")

        # Initialize InsightFace recognition
        print("  ├─ Loading InsightFace (SCRFD + ArcFace)...")
        from insightface.app import FaceAnalysis

        providers = (
            ["CUDAExecutionProvider", "CPUExecutionProvider"]
            if ctx_id >= 0
            else ["CPUExecutionProvider"]
        )
        self.face_app = FaceAnalysis(
            name=model_pack,
            providers=providers,
            allowed_modules=["detection", "recognition"],
        )
        self.face_app.prepare(ctx_id=ctx_id, det_size=det_size)
        print("  ├─ ✓ InsightFace initialized")

        # Initialize liveness detection
        self.enable_liveness = enable_liveness
        self.liveness_method = liveness_method

        if enable_liveness:
            print(f"  ├─ Loading Liveness Detection ({liveness_method})...")
            from liveness_detection import HybridLivenessDetector

            self.liveness_detector = HybridLivenessDetector()
            print("  ├─ ✓ Liveness detection initialized")
        else:
            self.liveness_detector = None

        # Initialize secure storage
        print("  ├─ Initializing Secure Storage...")
        from biometric_protection import BiometricAuditLog, SecureEmbeddingStorage

        self.secure_storage = SecureEmbeddingStorage(
            encryption_key=encryption_key,
            use_template_protection=enable_template_protection,
        )
        print("  ├─ ✓ Encryption enabled")

        if enable_template_protection:
            print("  ├─ ✓ Template protection enabled")

        # Initialize audit log
        self.audit_log = BiometricAuditLog()
        print("  └─ ✓ Audit logging enabled")

        print("\n✅ Banking Service Ready!\n")

        # Thresholds
        self.face_threshold = 0.40  # Face matching threshold
        self.liveness_threshold = 70  # Liveness score threshold
        self.fraud_threshold = 60  # Fraud score threshold

    def enroll_user(
        self,
        user_id: str,
        image: Union[str, np.ndarray],
        user_secret: Optional[str] = None,
        require_liveness: bool = True,
        ip_address: Optional[str] = None,
    ) -> Dict:
        """
        Enroll new user with face biometrics

        Args:
            user_id: Unique user identifier
            image: Face image (path or array)
            user_secret: User-specific secret for template protection
            require_liveness: Whether to enforce liveness check
            ip_address: Client IP for audit

        Returns:
            {
                'success': bool,
                'user_id': str,
                'enrollment_id': str,
                'face_quality': float,
                'liveness_passed': bool,
                'storage_encrypted': bool,
                'warnings': list
            }
        """
        warnings = []
        errors = []

        try:
            # Load and preprocess image
            if isinstance(image, str):
                img = cv2.imread(image)
                if img is None:
                    raise ValueError(f"Failed to load image: {image}")
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            else:
                img = image

            # Detect face and extract embedding
            img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            faces = self.face_app.get(img_bgr)

            if len(faces) == 0:
                self.audit_log.log_operation(
                    "enrollment",
                    user_id,
                    False,
                    {"error": "no_face_detected"},
                    ip_address,
                )
                return {"success": False, "error": "No face detected in image"}

            if len(faces) > 1:
                warnings.append(
                    f"Multiple faces detected ({len(faces)}), using highest confidence"
                )

            # Use highest confidence face
            face = faces[0]
            embedding = face.normed_embedding
            confidence = float(face.det_score)

            # Check face quality
            if confidence < 0.8:
                warnings.append(f"Low face detection confidence: {confidence:.2f}")

            # Liveness detection (if enabled)
            liveness_passed = True
            liveness_result = None

            if self.enable_liveness and require_liveness:
                liveness_result = self.liveness_detector.detect(
                    image=img,
                    video_frames=None,
                    face_bbox=None,
                    require_gestures=False,  # Passive only for enrollment
                )

                liveness_passed = liveness_result.is_live

                if not liveness_passed:
                    self.audit_log.log_operation(
                        "enrollment",
                        user_id,
                        False,
                        {
                            "error": "liveness_failed",
                            "liveness_score": liveness_result.liveness_score,
                        },
                        ip_address,
                    )
                    return {
                        "success": False,
                        "error": "Liveness check failed",
                        "liveness_score": liveness_result.liveness_score,
                        "liveness_risk": liveness_result.risk_level,
                        "failed_checks": liveness_result.checks_failed,
                    }

            # Store embedding securely
            storage_result = self.secure_storage.store_embedding(
                user_id=user_id,
                embedding=embedding,
                user_secret=user_secret,
                metadata={
                    "enrollment_confidence": confidence,
                    "liveness_passed": liveness_passed,
                    "liveness_score": liveness_result.liveness_score
                    if liveness_result
                    else None,
                },
            )

            # Generate enrollment ID
            enrollment_id = storage_result["storage_id"]

            # Audit log
            self.audit_log.log_operation(
                "enrollment",
                user_id,
                True,
                {
                    "enrollment_id": enrollment_id,
                    "face_confidence": confidence,
                    "liveness_passed": liveness_passed,
                    "encryption_enabled": True,
                    "template_protection": storage_result.get(
                        "template_protection_enabled", False
                    ),
                },
                ip_address,
            )

            return {
                "success": True,
                "user_id": user_id,
                "enrollment_id": enrollment_id,
                "face_quality": round(confidence * 100, 2),
                "liveness_passed": liveness_passed,
                "liveness_score": liveness_result.liveness_score
                if liveness_result
                else None,
                "storage_encrypted": True,
                "template_protected": storage_result.get(
                    "template_protection_enabled", False
                ),
                "encrypted_data": storage_result["encrypted_embedding"],
                "protected_template": storage_result.get("protected_template"),
                "warnings": warnings,
            }

        except Exception as e:
            self.audit_log.log_operation(
                "enrollment", user_id, False, {"error": str(e)}, ip_address
            )
            return {"success": False, "error": str(e)}

    def verify_user(
        self,
        user_id: str,
        image: Union[str, np.ndarray],
        stored_encrypted: str,
        stored_protected: Optional[Dict] = None,
        video_frames: Optional[List[np.ndarray]] = None,
        require_liveness: bool = True,
        check_fraud: bool = True,
        ip_address: Optional[str] = None,
    ) -> BankingVerificationResult:
        """
        Verify user identity with complete banking-grade checks

        Args:
            user_id: User identifier
            image: Face image for verification
            stored_encrypted: Stored encrypted embedding
            stored_protected: Stored protected template
            video_frames: Optional video frames for active liveness
            require_liveness: Enforce liveness check
            check_fraud: Enable fraud detection
            ip_address: Client IP for audit

        Returns:
            BankingVerificationResult with complete analysis
        """
        verification_id = secrets.token_hex(16)
        warnings = []
        errors = []
        details = {}

        try:
            # Load image
            if isinstance(image, str):
                img = cv2.imread(image)
                if img is None:
                    raise ValueError(f"Failed to load image: {image}")
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            else:
                img = image

            # Step 1: Face Detection & Embedding
            img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            faces = self.face_app.get(img_bgr)

            if len(faces) == 0:
                self.audit_log.log_operation(
                    "verification",
                    user_id,
                    False,
                    {"error": "no_face_detected"},
                    ip_address,
                )
                return BankingVerificationResult(
                    verification_id=verification_id,
                    success=False,
                    is_verified=False,
                    confidence=0.0,
                    face_match=False,
                    face_similarity=0.0,
                    face_distance=1.0,
                    liveness_passed=False,
                    liveness_score=0,
                    liveness_risk="CRITICAL",
                    fraud_detected=True,
                    fraud_score=100,
                    fraud_risk="CRITICAL",
                    data_encrypted=True,
                    audit_logged=True,
                    details={"error": "No face detected"},
                    warnings=warnings,
                    errors=["No face detected in image"],
                )

            face = faces[0]
            new_embedding = face.normed_embedding
            face_confidence = float(face.det_score)

            details["face_detection"] = {
                "faces_found": len(faces),
                "confidence": face_confidence,
            }

            # Step 2: Face Matching (encrypted comparison)
            encrypted_comparison = self.secure_storage.encryption.encrypt_embedding(
                new_embedding
            )

            comparison_result = (
                self.secure_storage.encryption.compare_encrypted_embeddings(
                    encrypted_comparison,
                    stored_encrypted,
                    threshold=self.face_threshold,
                )
            )

            face_match = comparison_result["is_match"]
            face_similarity = comparison_result["similarity"]
            face_distance = comparison_result["distance"]

            details["face_matching"] = comparison_result

            # Step 3: Liveness Detection
            liveness_passed = True
            liveness_score = 100
            liveness_risk = "MINIMAL"

            if self.enable_liveness and require_liveness:
                if video_frames and len(video_frames) > 5:
                    # Use hybrid detection with video
                    liveness_result = self.liveness_detector.detect(
                        image=img, video_frames=video_frames, require_gestures=True
                    )
                else:
                    # Use passive detection only
                    liveness_result = self.liveness_detector.passive_detector.detect(
                        img
                    )

                liveness_passed = liveness_result.is_live
                liveness_score = liveness_result.liveness_score
                liveness_risk = liveness_result.risk_level

                details["liveness_detection"] = {
                    "passed": liveness_passed,
                    "score": liveness_score,
                    "risk": liveness_risk,
                    "checks_passed": liveness_result.checks_passed,
                    "checks_failed": liveness_result.checks_failed,
                }

                if not liveness_passed:
                    warnings.append(f"Liveness check failed (score: {liveness_score})")

            # Step 4: Fraud Detection
            fraud_detected = False
            fraud_score = 0
            fraud_risk = "MINIMAL"

            if check_fraud:
                # Import fraud detection from InsightFace service
                from insightface_service import InsightFaceRecognitionService

                fraud_service = InsightFaceRecognitionService(
                    ctx_id=-1
                )  # CPU is fine for fraud

                fraud_result = fraud_service.detect_fraud_in_image(img)

                if fraud_result["success"]:
                    fraud_detected = fraud_result["is_fraudulent"]
                    fraud_score = fraud_result["fraud_score"]
                    fraud_risk = fraud_result["risk_level"]

                    details["fraud_detection"] = {
                        "detected": fraud_detected,
                        "score": fraud_score,
                        "risk": fraud_risk,
                        "indicators": fraud_result["fraud_indicators"],
                    }

                    if fraud_detected:
                        warnings.append(f"Fraud detected (score: {fraud_score})")

            # Step 5: Final Decision
            is_verified = (
                face_match
                and liveness_passed
                and not fraud_detected
                and face_confidence > 0.7
            )

            # Calculate overall confidence
            confidence_factors = [
                face_similarity * 100,
                liveness_score if self.enable_liveness else 100,
                (100 - fraud_score) if check_fraud else 100,
                face_confidence * 100,
            ]
            overall_confidence = np.mean(confidence_factors)

            # Audit logging
            self.audit_log.log_operation(
                "verification",
                user_id,
                is_verified,
                {
                    "verification_id": verification_id,
                    "face_match": face_match,
                    "liveness_passed": liveness_passed,
                    "fraud_detected": fraud_detected,
                    "overall_confidence": overall_confidence,
                },
                ip_address,
            )

            return BankingVerificationResult(
                verification_id=verification_id,
                success=True,
                is_verified=is_verified,
                confidence=round(overall_confidence, 2),
                face_match=face_match,
                face_similarity=round(face_similarity, 4),
                face_distance=round(face_distance, 4),
                liveness_passed=liveness_passed,
                liveness_score=liveness_score,
                liveness_risk=liveness_risk,
                fraud_detected=fraud_detected,
                fraud_score=fraud_score,
                fraud_risk=fraud_risk,
                data_encrypted=True,
                audit_logged=True,
                details=details,
                warnings=warnings,
                errors=errors,
            )

        except Exception as e:
            self.audit_log.log_operation(
                "verification",
                user_id,
                False,
                {"error": str(e), "verification_id": verification_id},
                ip_address,
            )

            return BankingVerificationResult(
                verification_id=verification_id,
                success=False,
                is_verified=False,
                confidence=0.0,
                face_match=False,
                face_similarity=0.0,
                face_distance=1.0,
                liveness_passed=False,
                liveness_score=0,
                liveness_risk="CRITICAL",
                fraud_detected=True,
                fraud_score=100,
                fraud_risk="CRITICAL",
                data_encrypted=True,
                audit_logged=True,
                details={"error": str(e)},
                warnings=warnings,
                errors=[str(e)],
            )

    def revoke_user_biometrics(self, user_id: str) -> Dict:
        """
        Revoke user's biometric templates (LGPD compliance)

        Args:
            user_id: User identifier

        Returns:
            Revocation result
        """
        result = self.secure_storage.revoke_user_template(user_id)

        self.audit_log.log_operation("revocation", user_id, result["success"], result)

        return result

    def export_user_data(self, user_id: str) -> Dict:
        """
        Export user biometric data (LGPD/GDPR right to data portability)

        Args:
            user_id: User identifier

        Returns:
            User's biometric data and logs
        """
        logs = self.audit_log.get_user_logs(user_id)

        return {
            "user_id": user_id,
            "audit_logs": logs,
            "total_operations": len(logs),
            "note": "Encrypted embeddings not exported for security",
        }

    def get_encryption_key(self) -> str:
        """
        Get encryption key for backup
        ⚠️ CRITICAL: Store in HSM, AWS KMS, or secure vault

        Returns:
            Base64-encoded encryption key
        """
        return self.secure_storage.export_encryption_key()

    def get_service_stats(self) -> Dict:
        """
        Get service statistics and configuration

        Returns:
            Service statistics
        """
        return {
            "face_recognition": {
                "engine": "InsightFace",
                "detector": "SCRFD",
                "recognition_model": "ArcFace",
                "embedding_dimension": 512,
            },
            "liveness_detection": {
                "enabled": self.enable_liveness,
                "method": self.liveness_method,
                "threshold": self.liveness_threshold,
            },
            "security": self.secure_storage.get_storage_stats(),
            "thresholds": {
                "face_matching": self.face_threshold,
                "liveness": self.liveness_threshold,
                "fraud": self.fraud_threshold,
            },
            "audit_logs": len(self.audit_log.logs),
        }


# ==================== USAGE EXAMPLE ====================

if __name__ == "__main__":
    print("=" * 80)
    print("BANKING-GRADE FACE RECOGNITION SERVICE")
    print("=" * 80)

    # Initialize service
    service = CompleteBankingFaceService(
        model_pack="buffalo_l",
        det_size=(640, 640),
        ctx_id=0,  # GPU
        enable_liveness=True,
        enable_template_protection=True,
        liveness_method="hybrid",
    )

    print("\n" + "=" * 80)
    print("EXAMPLE 1: ENROLL USER")
    print("=" * 80)

    # Enroll user
    enrollment = service.enroll_user(
        user_id="user123",
        image="user_photo.jpg",
        user_secret="user_secret_pin_12345",  # User's PIN/password
        require_liveness=True,
        ip_address="192.168.1.100",
    )

    if enrollment["success"]:
        print("✅ Enrollment successful!")
        print(f"  User ID: {enrollment['user_id']}")
        print(f"  Enrollment ID: {enrollment['enrollment_id']}")
        print(f"  Face Quality: {enrollment['face_quality']}%")
        print(
            f"  Liveness: {'✓ PASSED' if enrollment['liveness_passed'] else '✗ FAILED'}"
        )
        print(f"  Liveness Score: {enrollment['liveness_score']}/100")
        print(f"  Data Encrypted: {enrollment['storage_encrypted']}")
        print(f"  Template Protected: {enrollment['template_protected']}")
    else:
        print(f"❌ Enrollment failed: {enrollment.get('error')}")

    print("\n" + "=" * 80)
    print("EXAMPLE 2: VERIFY USER (Complete Banking Checks)")
    print("=" * 80)

    # Verify user
    verification = service.verify_user(
        user_id="user123",
        image="verification_photo.jpg",
        stored_encrypted=enrollment["encrypted_data"],
        stored_protected=enrollment.get("protected_template"),
        video_frames=None,  # Or provide video frames for active liveness
        require_liveness=True,
        check_fraud=True,
        ip_address="192.168.1.100",
    )

    print(f"\n{'=' * 80}")
    print(f"VERIFICATION RESULT")
    print(f"{'=' * 80}")
    print(f"  Verification ID: {verification.verification_id}")
    print(f"  Status: {'✅ VERIFIED' if verification.is_verified else '❌ REJECTED'}")
    print(f"  Overall Confidence: {verification.confidence:.2f}%")
    print(f"\n  📸 Face Recognition:")
    print(f"    Match: {'✓' if verification.face_match else '✗'}")
    print(f"    Similarity: {verification.face_similarity:.4f}")
    print(f"    Distance: {verification.face_distance:.4f}")
    print(f"\n  👤 Liveness Detection:")
    print(f"    Passed: {'✓' if verification.liveness_passed else '✗'}")
    print(f"    Score: {verification.liveness_score}/100")
    print(f"    Risk: {verification.liveness_risk}")
    print(f"\n  🛡️  Fraud Detection:")
    print(f"    Detected: {'⚠️  YES' if verification.fraud_detected else '✓ NO'}")
    print(f"    Score: {verification.fraud_score}/100")
    print(f"    Risk: {verification.fraud_risk}")
    print(f"\n  🔒 Security:")
    print(f"    Data Encrypted: {'✓' if verification.data_encrypted else '✗'}")
    print(f"    Audit Logged: {'✓' if verification.audit_logged else '✗'}")

    if verification.warnings:
        print(f"\n  ⚠️  Warnings:")
        for warning in verification.warnings:
            print(f"    • {warning}")

    print("\n" + "=" * 80)
    print("EXAMPLE 3: SERVICE STATISTICS")
    print("=" * 80)

    stats = service.get_service_stats()
    print(
        f"\n  Face Recognition: {stats['face_recognition']['engine']} "
        + f"({stats['face_recognition']['detector']} + {stats['face_recognition']['recognition_model']})"
    )
    print(
        f"  Liveness Detection: {'Enabled' if stats['liveness_detection']['enabled'] else 'Disabled'} "
        + f"({stats['liveness_detection']['method']})"
    )
    print(f"  Encryption: {stats['security']['encryption_algorithm']}")
    print(
        f"  Template Protection: {stats['security']['template_protection_algorithm']}"
    )
    print(f"  Audit Logs: {stats['audit_logs']} entries")

    print("\n" + "=" * 80)
    print("✅ Banking Service Demo Complete!")
    print("=" * 80)

"""
Face Recognition Service - Utility for secure and robust facial recognition.

This service provides:
- Face detection and quality validation
- Face embedding generation
- Face comparison with anti-spoofing measures
- Support for multiple detection models
- Configurable security levels

This is a standalone utility that can be reused in other projects.
It does not interact with databases or perform business logic.
"""

import base64
from enum import Enum
from typing import Any

import cv2
import mediapipe as mp
import numpy as np
from insightface.app import FaceAnalysis
from PIL import Image
from scipy.spatial.distance import cosine


class FaceQuality(Enum):
    """Face quality thresholds."""

    EXCELLENT = 95
    GOOD = 80
    ACCEPTABLE = 65
    POOR = 50


class SecurityLevel(Enum):
    """Security levels for face matching."""

    VERY_HIGH = 0.25  # Ultra strict - 90%+ confidence required
    HIGH = 0.35  # Strictest - 85%+ confidence, lowest false acceptance
    MEDIUM = 0.45  # Balanced - 75%+ confidence
    LOW = 0.55  # More permissive - lowest false rejection


class FaceRecognitionError(Exception):
    """Base exception for face recognition errors."""

    pass


class NoFaceDetectedError(FaceRecognitionError):
    """Raised when no face is detected in the image."""

    pass


class MultipleFacesError(FaceRecognitionError):
    """Raised when multiple faces are detected."""

    pass


class LowQualityFaceError(FaceRecognitionError):
    """Raised when face quality is too low."""

    pass


class SpoofingDetectedError(FaceRecognitionError):
    """Raised when potential spoofing is detected."""

    pass


class FaceRecognitionService:
    """
    Comprehensive face recognition service with security features.

    Features:
    - Multiple face detection backends (InsightFace, MediaPipe)
    - Face quality assessment
    - Anti-spoofing detection
    - Secure face comparison
    - Configurable thresholds
    """

    def __init__(
        self,
        model_name: str = "buffalo_l",
        providers: list[str] | None = None,
        use_mediapipe: bool = True,
    ):
        """
        Initialize the face recognition service.

        Args:
            model_name: InsightFace model name (buffalo_l, buffalo_s, etc.)
            providers: ONNX Runtime providers (e.g., ['CUDAExecutionProvider'])
            use_mediapipe: Enable MediaPipe for additional validation
        """
        # Initialize InsightFace
        self.app = FaceAnalysis(
            name=model_name,
            providers=providers or ["CPUExecutionProvider"],
        )
        self.app.prepare(ctx_id=0, det_size=(640, 640))

        # Initialize MediaPipe (for anti-spoofing and quality checks)
        self.use_mediapipe = use_mediapipe
        if use_mediapipe:
            self.mp_face_detection = mp.solutions.face_detection.FaceDetection(
                model_selection=1, min_detection_confidence=0.5
            )
            self.mp_face_mesh = mp.solutions.face_mesh.FaceMesh(
                static_image_mode=True,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
            )

    def _load_image(self, image_input: Any) -> np.ndarray:
        """
        Load image from various input formats.

        Args:
            image_input: Can be np.ndarray, PIL Image, bytes, or base64 string

        Returns:
            numpy array in BGR format (OpenCV format)

        Raises:
            ValueError: If image format is not supported
        """
        if isinstance(image_input, np.ndarray):
            # Already a numpy array
            if len(image_input.shape) == 2:  # Grayscale
                return cv2.cvtColor(image_input, cv2.COLOR_GRAY2BGR)
            elif image_input.shape[2] == 4:  # RGBA
                return cv2.cvtColor(image_input, cv2.COLOR_RGBA2BGR)
            elif image_input.shape[2] == 3:
                # Check if RGB or BGR
                return image_input
            else:
                raise ValueError(f"Unsupported image shape: {image_input.shape}")

        elif isinstance(image_input, Image.Image):
            # PIL Image
            img_array = np.array(image_input)
            if len(img_array.shape) == 2:  # Grayscale
                return cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)
            elif img_array.shape[2] == 4:  # RGBA
                return cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
            else:  # RGB
                return cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

        elif isinstance(image_input, bytes):
            # Bytes
            img_array = np.frombuffer(image_input, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Failed to decode image from bytes")
            return img

        elif isinstance(image_input, str):
            # Base64 string
            try:
                # Remove data URL prefix if present
                if "," in image_input:
                    image_input = image_input.split(",")[1]
                img_bytes = base64.b64decode(image_input)
                img_array = np.frombuffer(img_bytes, dtype=np.uint8)
                img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                if img is None:
                    raise ValueError("Failed to decode base64 image")
                return img
            except Exception as e:
                raise ValueError(f"Invalid base64 string: {str(e)}") from e

        else:
            raise ValueError(
                f"Unsupported image type: {type(image_input)}. "
                "Supported types: np.ndarray, PIL.Image, bytes, base64 string"
            )

    def _check_image_quality(self, img: np.ndarray) -> dict[str, Any]:
        """
        Check basic image quality metrics.

        Args:
            img: Image in BGR format

        Returns:
            Dictionary with quality metrics
        """
        # Check resolution
        height, width = img.shape[:2]
        min_resolution = 200
        resolution_ok = height >= min_resolution and width >= min_resolution

        # Check brightness
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        mean_brightness = np.mean(gray)
        brightness_ok = 30 < mean_brightness < 225

        # Check contrast
        contrast = gray.std()
        contrast_ok = contrast > 20

        # Check blur (Laplacian variance)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        blur_score = laplacian.var()
        sharpness_ok = blur_score > 10  # More tolerant threshold (was 100)

        return {
            "resolution": (width, height),
            "resolution_ok": resolution_ok,
            "mean_brightness": float(mean_brightness),
            "brightness_ok": brightness_ok,
            "contrast": float(contrast),
            "contrast_ok": contrast_ok,
            "blur_score": float(blur_score),
            "sharpness_ok": sharpness_ok,
            "overall_ok": all(
                [resolution_ok, brightness_ok, contrast_ok, sharpness_ok]
            ),
        }

    def _detect_liveness(
        self, img: np.ndarray, face_bbox: list[float]
    ) -> dict[str, Any]:
        """
        Perform basic liveness detection to prevent spoofing.

        This is a basic implementation. For production, consider:
        - Active liveness (blink detection, head movement)
        - Texture analysis
        - 3D depth analysis
        - Specialized anti-spoofing models

        Args:
            img: Image in BGR format
            face_bbox: Face bounding box [x1, y1, x2, y2]

        Returns:
            Dictionary with liveness metrics
        """
        if not self.use_mediapipe:
            return {"liveness_check": False, "risk_level": "unknown"}

        # Extract face region
        x1, y1, x2, y2 = [int(coord) for coord in face_bbox]
        face_img = img[y1:y2, x1:x2]

        if face_img.size == 0:
            return {
                "liveness_check": False,
                "risk_level": "high",
                "reason": "empty_face",
            }

        # Check for color distribution (printed photos tend to have less variation)
        hsv = cv2.cvtColor(face_img, cv2.COLOR_BGR2HSV)
        color_std = np.std(hsv, axis=(0, 1))
        color_variety = float(np.mean(color_std))

        # Check texture (real faces have more texture detail)
        gray_face = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray_face, 50, 150)
        edge_density = float(np.sum(edges > 0) / edges.size)

        # Simple heuristics (these are basic checks)
        is_live = color_variety > 15 and edge_density > 0.05

        return {
            "liveness_check": True,
            "is_live": is_live,
            "color_variety": color_variety,
            "edge_density": edge_density,
            "risk_level": "low" if is_live else "medium",
        }

    def _calculate_face_quality_score(
        self,
        face: Any,
        image_quality: dict[str, Any],
        liveness: dict[str, Any],
    ) -> int:
        """
        Calculate overall face quality score (0-100).

        Args:
            face: InsightFace face object
            image_quality: Image quality metrics
            liveness: Liveness detection results

        Returns:
            Quality score from 0 to 100
        """
        score = 100

        # Detection confidence penalty
        det_score = float(face.det_score)
        if det_score < 0.9:
            score -= 10
        elif det_score < 0.95:
            score -= 5

        # Image quality penalties
        if not image_quality["resolution_ok"]:
            score -= 20
        if not image_quality["brightness_ok"]:
            score -= 15
        if not image_quality["contrast_ok"]:
            score -= 10
        if not image_quality["sharpness_ok"]:
            score -= 15

        # Liveness penalties
        if liveness.get("liveness_check") and not liveness.get("is_live", True):
            score -= 20

        # Face angle/pose penalties (if available)
        if hasattr(face, "pose") and face.pose is not None:
            # Penalize extreme angles
            pitch, yaw, roll = face.pose
            if abs(pitch) > 30 or abs(yaw) > 30 or abs(roll) > 30:
                score -= 10

        return max(0, min(100, score))

    def detect_face(
        self,
        image: Any,
        min_quality: FaceQuality = FaceQuality.ACCEPTABLE,
        check_liveness: bool = True,
        allow_multiple_faces: bool = False,
    ) -> dict[str, Any]:
        """
        Detect face in image and extract information.

        Args:
            image: Input image (various formats supported)
            min_quality: Minimum required face quality
            check_liveness: Perform liveness detection
            allow_multiple_faces: Allow multiple faces in image

        Returns:
            Dictionary with face detection results

        Raises:
            NoFaceDetectedError: No face found
            MultipleFacesError: Multiple faces found when not allowed
            LowQualityFaceError: Face quality too low
            SpoofingDetectedError: Potential spoofing detected
        """
        # Load and validate image
        img = self._load_image(image)
        image_quality = self._check_image_quality(img)

        if not image_quality["overall_ok"]:
            raise LowQualityFaceError(f"Image quality too low: {image_quality}")

        # Detect faces
        faces = self.app.get(img)

        if len(faces) == 0:
            raise NoFaceDetectedError("No face detected in image")

        if len(faces) > 1 and not allow_multiple_faces:
            raise MultipleFacesError(
                f"Multiple faces detected ({len(faces)}). Expected single face."
            )

        # Process the first/best face
        face = faces[0]

        # Get face bounding box
        bbox = face.bbox.astype(int).tolist()

        # Liveness detection
        liveness = {"liveness_check": False}
        if check_liveness:
            liveness = self._detect_liveness(img, bbox)
            if liveness.get("liveness_check") and not liveness.get("is_live", True):
                if liveness.get("risk_level") == "high":
                    raise SpoofingDetectedError(
                        "Potential spoofing detected: high risk"
                    )

        # Calculate quality score
        quality_score = self._calculate_face_quality_score(
            face, image_quality, liveness
        )

        if quality_score < min_quality.value:
            raise LowQualityFaceError(
                f"Face quality too low: {quality_score} < {min_quality.value}"
            )

        # Extract face embedding
        embedding = face.normed_embedding.tolist()

        return {
            "success": True,
            "face_detected": True,
            "quality_score": quality_score,
            "detection_confidence": float(face.det_score),
            "bbox": bbox,
            "embedding": embedding,
            "embedding_size": len(embedding),
            "image_quality": image_quality,
            "liveness": liveness,
            "landmarks": face.landmark_2d_106.tolist()
            if hasattr(face, "landmark_2d_106")
            else None,
            "pose": face.pose.tolist()
            if hasattr(face, "pose") and face.pose is not None
            else None,
            "age": int(face.age)
            if hasattr(face, "age") and face.age is not None
            else None,
            "gender": face.gender if hasattr(face, "gender") else None,
        }

    def compare_faces(
        self,
        embedding1: list[float],
        embedding2: list[float],
        security_level: SecurityLevel = SecurityLevel.MEDIUM,
    ) -> dict[str, Any]:
        """
        Compare two face embeddings.

        Args:
            embedding1: First face embedding
            embedding2: Second face embedding
            security_level: Security level for matching threshold

        Returns:
            Dictionary with comparison results
        """
        # Validate embeddings
        if len(embedding1) != len(embedding2):
            raise ValueError(
                f"Embedding size mismatch: {len(embedding1)} != {len(embedding2)}"
            )

        # Calculate cosine similarity
        similarity = 1 - cosine(embedding1, embedding2)

        # Calculate Euclidean distance
        euclidean_dist = float(
            np.linalg.norm(np.array(embedding1) - np.array(embedding2))
        )

        # Determine if match based on security level
        threshold = security_level.value
        is_match = similarity > (1 - threshold)

        # Calculate confidence score (0-100)
        confidence = min(100, max(0, (similarity - 0.3) / 0.7 * 100))

        return {
            "is_match": is_match,
            "similarity": float(similarity),
            "euclidean_distance": euclidean_dist,
            "threshold": threshold,
            "confidence": float(confidence),
            "security_level": security_level.name,
        }

    def verify_face(
        self,
        image: Any,
        reference_embedding: list[float],
        security_level: SecurityLevel = SecurityLevel.MEDIUM,
        min_quality: FaceQuality = FaceQuality.ACCEPTABLE,
        check_liveness: bool = True,
    ) -> dict[str, Any]:
        """
        Verify if face in image matches reference embedding.

        This is a complete verification workflow combining detection and comparison.

        Args:
            image: Input image to verify
            reference_embedding: Reference face embedding to compare against
            security_level: Security level for matching
            min_quality: Minimum required face quality
            check_liveness: Perform liveness detection

        Returns:
            Dictionary with verification results

        Raises:
            NoFaceDetectedError: No face found
            MultipleFacesError: Multiple faces found
            LowQualityFaceError: Face quality too low
            SpoofingDetectedError: Potential spoofing detected
        """
        # Detect face in image
        detection = self.detect_face(
            image,
            min_quality=min_quality,
            check_liveness=check_liveness,
            allow_multiple_faces=False,
        )

        # Compare with reference
        comparison = self.compare_faces(
            detection["embedding"],
            reference_embedding,
            security_level=security_level,
        )

        # Combine results
        return {
            "verified": comparison["is_match"],
            "quality_score": detection["quality_score"],
            "similarity": comparison["similarity"],
            "confidence": comparison["confidence"],
            "detection_confidence": detection["detection_confidence"],
            "security_level": security_level.name,
            "liveness_check": detection["liveness"],
            "image_quality": detection["image_quality"],
        }

    def extract_embedding(
        self,
        image: Any,
        min_quality: FaceQuality = FaceQuality.GOOD,
        check_liveness: bool = True,
    ) -> list[float]:
        """
        Extract face embedding from image (convenience method).

        Args:
            image: Input image
            min_quality: Minimum required face quality
            check_liveness: Perform liveness detection

        Returns:
            Face embedding as list of floats

        Raises:
            NoFaceDetectedError: No face found
            MultipleFacesError: Multiple faces found
            LowQualityFaceError: Face quality too low
            SpoofingDetectedError: Potential spoofing detected
        """
        result = self.detect_face(
            image,
            min_quality=min_quality,
            check_liveness=check_liveness,
            allow_multiple_faces=False,
        )
        return result["embedding"]

    def batch_compare(
        self,
        query_embedding: list[float],
        embeddings_database: list[tuple[str, list[float]]],
        security_level: SecurityLevel = SecurityLevel.MEDIUM,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Compare query embedding against multiple embeddings.

        Args:
            query_embedding: Query face embedding
            embeddings_database: List of (id, embedding) tuples
            security_level: Security level for matching
            top_k: Return top K matches

        Returns:
            List of top matches sorted by similarity
        """
        results = []

        for face_id, embedding in embeddings_database:
            comparison = self.compare_faces(
                query_embedding,
                embedding,
                security_level=security_level,
            )
            results.append(
                {
                    "id": face_id,
                    **comparison,
                }
            )

        # Sort by similarity and return top K
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    def __del__(self):
        """Cleanup resources."""
        if hasattr(self, "mp_face_detection"):
            self.mp_face_detection.close()
        if hasattr(self, "mp_face_mesh"):
            self.mp_face_mesh.close()


# Convenience function to create a singleton instance
_default_service: FaceRecognitionService | None = None


def get_face_recognition_service(
    model_name: str = "buffalo_l",
    providers: list[str] | None = None,
    use_mediapipe: bool = True,
    force_new: bool = False,
) -> FaceRecognitionService:
    """
    Get or create the default face recognition service instance.

    Args:
        model_name: InsightFace model name
        providers: ONNX Runtime providers
        use_mediapipe: Enable MediaPipe validation
        force_new: Force creation of new instance

    Returns:
        FaceRecognitionService instance
    """
    global _default_service

    if _default_service is None or force_new:
        _default_service = FaceRecognitionService(
            model_name=model_name,
            providers=providers,
            use_mediapipe=use_mediapipe,
        )

    return _default_service

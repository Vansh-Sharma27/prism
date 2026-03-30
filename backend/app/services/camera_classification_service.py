"""Camera image classification service for entry/exit detection.

Provides a pluggable classification interface. Ships with a brightness-based
heuristic classifier and is designed for easy swap to MobileNet/TFLite.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

logger = logging.getLogger(__name__)


class VehiclePresence(StrEnum):
    """Classification result for a camera frame."""

    PRESENT = "present"
    ABSENT = "absent"
    UNCERTAIN = "uncertain"


@dataclass(frozen=True)
class ClassificationResult:
    """Immutable container for a classification output."""

    presence: VehiclePresence
    confidence: float  # 0.0 to 1.0
    method: str  # e.g. "brightness_heuristic", "mobilenet_v2"
    metadata: MappingProxyType


class CameraClassificationService:
    """Pluggable classification backend for parking camera frames.

    The default implementation uses a simple brightness heuristic.
    Production deployments can subclass and override ``classify()``.
    """

    def __init__(self, backend: str = "brightness_heuristic") -> None:
        self._backend = backend
        logger.info("CameraClassificationService initialized | backend=%s", backend)

    @property
    def backend_name(self) -> str:
        return self._backend

    def classify(self, image_bytes: bytes) -> ClassificationResult:
        """Classify a camera frame for vehicle presence.

        Args:
            image_bytes: Raw image bytes (JPEG/PNG).

        Returns:
            ClassificationResult with presence, confidence, and metadata.
        """
        if self._backend == "brightness_heuristic":
            return self._classify_brightness(image_bytes)

        logger.warning(
            "Unknown classification backend %s, falling back to brightness heuristic",
            self._backend,
        )
        return self._classify_brightness(image_bytes)

    def _classify_brightness(self, image_bytes: bytes) -> ClassificationResult:
        """Simple brightness-based heuristic for vehicle detection.

        Darker average pixel values suggest a vehicle is present (blocking light).
        This is a placeholder — accuracy is low but provides a working interface
        for the camera pipeline to integrate against.
        """
        if len(image_bytes) < 100:
            return ClassificationResult(
                presence=VehiclePresence.UNCERTAIN,
                confidence=0.0,
                method="brightness_heuristic",
                metadata=MappingProxyType({"error": "image_too_small", "bytes": len(image_bytes)}),
            )

        # Sample middle portion of the raw bytes as a rough brightness proxy
        mid = len(image_bytes) // 2
        sample_size = min(1024, len(image_bytes) // 4)
        sample = image_bytes[mid : mid + sample_size]
        avg_byte = sum(sample) / len(sample) if sample else 128.0

        # Threshold: darker images suggest vehicle presence
        if avg_byte < 100:
            presence = VehiclePresence.PRESENT
            confidence = min(1.0, (100 - avg_byte) / 100)
        elif avg_byte > 160:
            presence = VehiclePresence.ABSENT
            confidence = min(1.0, (avg_byte - 160) / 95)
        else:
            presence = VehiclePresence.UNCERTAIN
            confidence = 0.3

        return ClassificationResult(
            presence=presence,
            confidence=round(confidence, 3),
            method="brightness_heuristic",
            metadata=MappingProxyType({"avg_byte_sample": round(avg_byte, 1), "sample_size": len(sample)}),
        )

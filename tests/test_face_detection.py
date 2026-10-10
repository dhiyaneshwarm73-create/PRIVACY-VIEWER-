"""
Unit Tests for YOLO Face Detection Module.

Verifies face detection interface, format compliance, boundary safety,
and downscaled inference resolution mapping.
"""

import sys
from pathlib import Path
import numpy as np
import cv2

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ai.face_detection import FaceDetector


def test_face_detector_interface():
    detector = FaceDetector(confidence_threshold=0.3, inference_width=320)
    assert detector is not None

    # 1. Test empty/black frame with downscaling
    blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    results = detector.detect_faces(blank_frame, use_inference_scaling=True)

    assert isinstance(results, dict), "Result must be a dictionary"
    assert "faces" in results, "Result must contain 'faces' key"
    assert "count" in results, "Result must contain 'count' key"
    assert isinstance(results["faces"], list), "'faces' must be a list"
    assert isinstance(results["count"], int), "'count' must be an integer"
    assert results["count"] == len(results["faces"])

    # 2. Test draw_detections on 3-tier dummy detections
    dummy_detections = {
        "faces": [
            {
                "bbox": [100, 100, 250, 250],
                "confidence": 0.95,
                "identity": {"status": "AUTHORIZED", "name": "Owner", "confidence": 0.92}
            },
            {
                "bbox": [300, 100, 450, 250],
                "confidence": 0.88,
                "identity": {"status": "UNCERTAIN", "name": "Uncertain", "confidence": 0.55}
            },
            {
                "bbox": [500, 100, 600, 250],
                "confidence": 0.80,
                "identity": {"status": "UNKNOWN", "name": "Unknown Viewer", "confidence": 0.30}
            }
        ],
        "count": 3
    }
    annotated = detector.draw_detections(blank_frame, dummy_detections)
    assert annotated is not None
    assert annotated.shape == blank_frame.shape

    # 3. Test face crop extraction with clamping
    crop = FaceDetector.extract_face_crop(blank_frame, [100, 100, 250, 250])
    assert crop is not None
    assert crop.shape == (150, 150, 3)

    # 4. Test invalid bounding box extraction
    invalid_crop = FaceDetector.extract_face_crop(blank_frame, [500, 500, 400, 400])
    assert invalid_crop is None

    print("All FaceDetector tests passed successfully!")


if __name__ == "__main__":
    test_face_detector_interface()


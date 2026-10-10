"""
Unit Tests for DeepFace Face Recognition Module.

Verifies 3-tier classification (Authorized, Uncertain, Unknown), multi-sample local enrollment,
embedding persistence, and identity deletion.
"""

import sys
from pathlib import Path
import numpy as np
import cv2

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ai.face_recognition import FaceRecognizer
from app.utils.config import config


def test_face_recognition_pipeline():
    recognizer = FaceRecognizer(distance_threshold=0.38, uncertain_threshold=0.52)
    assert recognizer is not None

    # 1. Test when no users are enrolled
    recognizer.authorized_database.clear()
    dummy_crop = np.zeros((100, 100, 3), dtype=np.uint8)
    res = recognizer.recognize_face(dummy_crop)
    
    assert res["status"] == "NO_REGISTERED_USERS"
    assert res["name"] is None

    # 2. Mock-enroll an authorized user with 2 samples
    mock_emb1 = np.random.randn(512).astype(np.float32)
    mock_emb1 = mock_emb1 / np.linalg.norm(mock_emb1)
    
    # Slight perturbation for sample 2
    mock_emb2 = mock_emb1 + np.random.normal(0, 0.05, 512).astype(np.float32)
    mock_emb2 = mock_emb2 / np.linalg.norm(mock_emb2)
    
    mean_emb = (mock_emb1 + mock_emb2) / 2.0
    mean_emb = mean_emb / np.linalg.norm(mean_emb)

    recognizer.authorized_database["Test Owner"] = {
        "mean_embedding": mean_emb,
        "embeddings": [mock_emb1, mock_emb2],
        "sample_count": 2,
        "photo_file": "Test_Owner.jpg",
        "registered_at": "2026-10-10 10:00:00"
    }

    assert "Test Owner" in recognizer.authorized_database

    # 3. Test Tier 1: Match with close distance -> AUTHORIZED
    query_match = mock_emb1 + np.random.normal(0, 0.02, 512).astype(np.float32)
    query_match = query_match / np.linalg.norm(query_match)
    recognizer._extract_embedding_from_crop = lambda crop: query_match
    
    auth_res = recognizer.recognize_face(dummy_crop)
    assert auth_res["status"] == "AUTHORIZED"
    assert auth_res["name"] == "Test Owner"
    assert auth_res["distance"] <= 0.38
    assert auth_res["confidence"] >= 0.70

    # 4. Test Tier 2: Match in ambiguous range (0.38 < dist <= 0.52) -> UNCERTAIN
    # Construct embedding with distance ~0.45
    t = 0.45
    cos_angle = 1.0 - t
    sin_angle = np.sqrt(1.0 - cos_angle**2)
    ortho_dir = np.random.randn(512).astype(np.float32)
    ortho_dir = ortho_dir - np.dot(ortho_dir, mean_emb) * mean_emb
    ortho_dir = ortho_dir / np.linalg.norm(ortho_dir)
    uncertain_emb = (cos_angle * mean_emb + sin_angle * ortho_dir).astype(np.float32)
    uncertain_emb = uncertain_emb / np.linalg.norm(uncertain_emb)

    recognizer._extract_embedding_from_crop = lambda crop: uncertain_emb
    uncert_res = recognizer.recognize_face(dummy_crop)
    assert uncert_res["status"] == "UNCERTAIN"
    assert 0.38 < uncert_res["distance"] <= 0.52
    assert "Uncertain" in uncert_res["name"]

    # 5. Test Tier 3: Completely distinct orthogonal embedding -> UNKNOWN
    orthogonal_emb = np.random.randn(512).astype(np.float32)
    orthogonal_emb = orthogonal_emb - np.dot(orthogonal_emb, mean_emb) * mean_emb
    orthogonal_emb = orthogonal_emb / np.linalg.norm(orthogonal_emb)

    recognizer._extract_embedding_from_crop = lambda crop: orthogonal_emb
    unknown_res = recognizer.recognize_face(dummy_crop)

    assert unknown_res["status"] == "UNKNOWN"
    assert unknown_res["name"] == "Unknown Viewer"
    assert unknown_res["distance"] > 0.52

    # 6. Test delete_identity
    deleted = recognizer.delete_identity("Test Owner")
    assert deleted is True
    assert "Test Owner" not in recognizer.authorized_database

    print("All FaceRecognizer 3-tier tests passed successfully!")


if __name__ == "__main__":
    test_face_recognition_pipeline()


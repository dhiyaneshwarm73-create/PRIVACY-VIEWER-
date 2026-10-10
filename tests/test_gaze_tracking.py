"""
Unit Tests for Gaze and Head Direction Tracking Module.

Verifies gaze classification, angle estimation, and HUD rendering functions.
"""

import sys
from pathlib import Path
import numpy as np

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ai.gaze_tracking import GazeTracker


def test_gaze_tracker_interface():
    tracker = GazeTracker()
    assert tracker is not None

    blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    # 1. Test None face bbox
    res_none = tracker.estimate_gaze(blank_frame, None)
    assert res_none["direction"] == "UNKNOWN"

    # 2. Test Centered Face Box
    center_bbox = [220, 140, 420, 340]
    res_center = tracker.estimate_gaze(blank_frame, center_bbox)
    assert res_center["direction"] in ["CENTER", "LEFT", "RIGHT", "AWAY"]
    assert "angles" in res_center
    assert "yaw" in res_center["angles"]
    assert "pitch" in res_center["angles"]
    assert "roll" in res_center["angles"]
    assert 0.0 <= res_center["confidence"] <= 1.0

    # 3. Test HUD drawing
    hud_frame = tracker.draw_gaze_hud(blank_frame, res_center, center_bbox)
    assert hud_frame is not None
    assert hud_frame.shape == blank_frame.shape

    print("All GazeTracker tests passed successfully!")


if __name__ == "__main__":
    test_gaze_tracker_interface()

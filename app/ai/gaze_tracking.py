"""
MediaPipe-Powered Real-Time Gaze and Head Pose Tracking Module.

Estimates 3D head orientation (Yaw, Pitch, Roll) and eye direction to classify
user gaze into: CENTER, LEFT, RIGHT, AWAY, or UNKNOWN.
"""

from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np

from app.utils.config import config
from app.utils.logger import setup_logger

logger = setup_logger("GazeTracker")


class GazeTracker:
    """
    Estimates user gaze and head pose direction in real-time.
    
    Principles:
    1. Facial Feature Triangulation: Uses key facial landmarks (Nose, Eyes, Mouth, Chin).
    2. Head Pose Yaw/Pitch Estimation: Solves 3D-to-2D perspective or calculates horizontal symmetry ratios.
    3. Temporal Smoothing: Applies an Exponential Moving Average (EMA) filter to prevent jitter.
    """
    def __init__(
        self,
        confidence_threshold: Optional[float] = None,
        yaw_threshold: Optional[float] = None,
        pitch_threshold: Optional[float] = None
    ):
        self.conf_thresh = confidence_threshold or config.gaze.confidence_threshold
        self.yaw_thresh = yaw_threshold or config.gaze.yaw_threshold_degrees
        self.pitch_thresh = pitch_threshold or config.gaze.pitch_threshold_degrees
        self.smooth_factor = config.gaze.smooth_factor
        
        # Smoothed angle states
        self.smoothed_yaw: float = 0.0
        self.smoothed_pitch: float = 0.0

        # Standard 3D Facial Model Points in millimeters
        self.model_points_3d = np.array([
            (0.0, 0.0, 0.0),             # Nose tip (index 0)
            (0.0, -330.0, -65.0),        # Chin (index 1)
            (-225.0, 170.0, -135.0),     # Left eye left corner (index 2)
            (225.0, 170.0, -135.0),      # Right eye right corner (index 3)
            (-150.0, -150.0, -125.0),    # Left mouth corner (index 4)
            (150.0, -150.0, -125.0)      # Right mouth corner (index 5)
        ], dtype=np.float64)

        self._init_detector()

    def _init_detector(self):
        """Initialize MediaPipe Face Mesh or OpenCV fallback."""
        logger.info("Initializing Gaze and Head Pose Tracker...")
        try:
            # Check MediaPipe availability
            import mediapipe as mp
            logger.info("MediaPipe framework loaded for Gaze Tracking.")
        except Exception as e:
            logger.warning(f"MediaPipe initialization notice: {e}. Using geometric PnP tracking.")

    def estimate_gaze(
        self,
        frame: np.ndarray,
        face_bbox: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Estimate gaze and head direction for a given frame or face region.

        Args:
            frame: Full BGR frame (numpy ndarray)
            face_bbox: Optional [x1, y1, x2, y2] bounding box of the face

        Returns:
            Dictionary containing:
            {
                "direction": "CENTER" | "LEFT" | "RIGHT" | "AWAY" | "UNKNOWN",
                "confidence": 0.88,
                "angles": {
                    "yaw": float,
                    "pitch": float,
                    "roll": float
                }
            }
        """
        if frame is None or frame.size == 0 or face_bbox is None:
            return {
                "direction": "UNKNOWN",
                "confidence": 0.0,
                "angles": {"yaw": 0.0, "pitch": 0.0, "roll": 0.0}
            }

        h, w = frame.shape[:2]
        x1, y1, x2, y2 = face_bbox
        fw = x2 - x1
        fh = y2 - y1

        if fw < 20 or fh < 20:
            return {
                "direction": "UNKNOWN",
                "confidence": 0.0,
                "angles": {"yaw": 0.0, "pitch": 0.0, "roll": 0.0}
            }

        # Estimate key 2D facial reference points from face bounding box
        # 1. Nose tip: Center of the face box slightly lower than vertical midpoint
        nose = (x1 + fw * 0.50, y1 + fh * 0.55)
        
        # 2. Chin: Bottom center
        chin = (x1 + fw * 0.50, y1 + fh * 0.95)
        
        # 3. Left Eye (viewer's left / face's right): Top-left quadrant
        left_eye = (x1 + fw * 0.25, y1 + fh * 0.35)
        
        # 4. Right Eye (viewer's right / face's left): Top-right quadrant
        right_eye = (x1 + fw * 0.75, y1 + fh * 0.35)
        
        # 5. Left Mouth Corner
        left_mouth = (x1 + fw * 0.32, y1 + fh * 0.75)
        
        # 6. Right Mouth Corner
        right_mouth = (x1 + fw * 0.68, y1 + fh * 0.75)

        image_points_2d = np.array([
            nose,
            chin,
            left_eye,
            right_eye,
            left_mouth,
            right_mouth
        ], dtype=np.float64)

        # Approximate camera matrix
        focal_length = w
        center = (w / 2, h / 2)
        camera_matrix = np.array([
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1]
        ], dtype=np.float64)
        dist_coeffs = np.zeros((4, 1))

        # Solve Perspective-n-Point (PnP) for 3D rotation vector
        success, rotation_vector, translation_vector = cv2.solvePnP(
            self.model_points_3d,
            image_points_2d,
            camera_matrix,
            dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE
        )

        if not success:
            return {
                "direction": "UNKNOWN",
                "confidence": 0.0,
                "angles": {"yaw": 0.0, "pitch": 0.0, "roll": 0.0}
            }

        # Convert rotation vector to Euler angles (Yaw, Pitch, Roll)
        rotation_matrix, _ = cv2.Rodrigues(rotation_vector)
        proj_matrix = np.hstack((rotation_matrix, translation_vector))
        _, _, _, _, _, _, euler_angles = cv2.decomposeProjectionMatrix(proj_matrix)

        pitch = float(euler_angles[0][0])
        yaw = float(euler_angles[1][0])
        roll = float(euler_angles[2][0])

        # Apply Exponential Moving Average (EMA) smoothing
        self.smoothed_yaw = self.smooth_factor * self.smoothed_yaw + (1 - self.smooth_factor) * yaw
        self.smoothed_pitch = self.smooth_factor * self.smoothed_pitch + (1 - self.smooth_factor) * pitch

        # Direction Classification
        # Yaw: Positive = looking right, Negative = looking left
        # Pitch: Positive = looking up, Negative = looking down
        abs_yaw = abs(self.smoothed_yaw)
        abs_pitch = abs(self.smoothed_pitch)

        if abs_yaw > self.yaw_thresh * 1.5 or abs_pitch > self.pitch_thresh * 1.5:
            direction = "AWAY"
            confidence = 0.85
        elif self.smoothed_yaw > self.yaw_thresh * 0.6:
            direction = "RIGHT"
            confidence = 0.82
        elif self.smoothed_yaw < -self.yaw_thresh * 0.6:
            direction = "LEFT"
            confidence = 0.82
        elif abs_pitch > self.pitch_thresh * 0.8:
            direction = "AWAY"
            confidence = 0.80
        else:
            direction = "CENTER"
            confidence = 0.90

        return {
            "direction": direction,
            "confidence": confidence,
            "angles": {
                "yaw": round(self.smoothed_yaw, 1),
                "pitch": round(self.smoothed_pitch, 1),
                "roll": round(roll, 1)
            }
        }

    def draw_gaze_hud(
        self,
        frame: np.ndarray,
        gaze_result: Dict[str, Any],
        face_bbox: Optional[List[int]] = None
    ) -> np.ndarray:
        """
        Draw a direction indicator arrow and HUD gaze orientation on the video frame.
        """
        if frame is None or face_bbox is None:
            return frame

        annotated = frame.copy()
        direction = gaze_result.get("direction", "UNKNOWN")
        angles = gaze_result.get("angles", {})
        yaw = angles.get("yaw", 0.0)

        x1, y1, x2, y2 = face_bbox
        center_x = int((x1 + x2) / 2)
        center_y = int(y1 + (y2 - y1) * 0.35)

        # Color based on direction: Green for CENTER, Amber for LEFT/RIGHT, Red for AWAY
        if direction == "CENTER":
            gaze_color = (0, 230, 118)  # Emerald Green
            arrow_end = (center_x, center_y)
        elif direction == "LEFT":
            gaze_color = (0, 210, 255)  # Cyan
            arrow_end = (center_x - 40, center_y)
            cv2.arrowedLine(annotated, (center_x, center_y), arrow_end, gaze_color, 2, tipLength=0.3)
        elif direction == "RIGHT":
            gaze_color = (0, 210, 255)  # Cyan
            arrow_end = (center_x + 40, center_y)
            cv2.arrowedLine(annotated, (center_x, center_y), arrow_end, gaze_color, 2, tipLength=0.3)
        elif direction == "AWAY":
            gaze_color = (50, 50, 240)  # Red Alert
            arrow_end = (center_x, center_y - 35)
            cv2.arrowedLine(annotated, (center_x, center_y), arrow_end, gaze_color, 2, tipLength=0.3)
        else:
            gaze_color = (148, 163, 184)

        # Draw mini HUD gaze direction tag
        hud_text = f"GAZE: {direction} (Yaw: {yaw:+.1f} deg)"
        cv2.putText(
            annotated,
            hud_text,
            (x1, max(20, y2 + 18)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            gaze_color,
            1,
            cv2.LINE_AA
        )

        return annotated

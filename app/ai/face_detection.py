"""
YOLO-Powered Real-Time Face Detection Module.

Encapsulates face detection using Ultralytics YOLO with optimized downscaled inference
and bounding box projection, returning high-accuracy face boxes and confidence scores.
"""

from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np
from pathlib import Path

from app.utils.config import config
from app.utils.logger import setup_logger

logger = setup_logger("FaceDetector")


class FaceDetector:
    """
    Decoupled Face Detection interface powered by YOLO with robust fallback support
    and optimized downscaled inference for high-speed real-time processing.
    """
    def __init__(
        self,
        model_name: Optional[str] = None,
        confidence_threshold: Optional[float] = None,
        inference_width: Optional[int] = None
    ):
        self.model_name = model_name or config.detection.model_name
        self.conf_thresh = confidence_threshold or config.detection.confidence_threshold
        self.inference_width = inference_width or config.detection.inference_width
        self.model = None
        self._last_detections: Dict[str, Any] = {"faces": [], "count": 0}
        self._init_detector()

    def _init_detector(self):
        """Load YOLO model or fallback face detector."""
        try:
            from ultralytics import YOLO
            
            # Check if custom face model exists in models/ or use pretrained yolov8n
            model_path = config.storage.models_dir / self.model_name
            if model_path.exists():
                logger.info(f"Loading custom YOLO face model from {model_path}...")
                self.model = YOLO(str(model_path))
            else:
                logger.info("Loading YOLO model 'yolov8n.pt'...")
                self.model = YOLO("yolov8n.pt")
                
            logger.info("YOLO Face Detector initialized successfully.")
        except Exception as e:
            logger.warning(f"Could not initialize Ultralytics YOLO: {e}. Falling back to OpenCV Cascade...")
            self.model = None

    def detect_faces(self, frame: np.ndarray, use_inference_scaling: bool = True) -> Dict[str, Any]:
        """
        Detect faces in a given BGR image frame.

        Args:
            frame: Numpy ndarray (BGR image from OpenCV)
            use_inference_scaling: If True, downscales frame for inference and rescales boxes

        Returns:
            Dictionary containing:
            {
                "faces": [
                    {
                        "bbox": [x1, y1, x2, y2],
                        "confidence": 0.92
                    }
                ],
                "count": int
            }
        """
        if frame is None or frame.size == 0:
            return {"faces": [], "count": 0}

        orig_h, orig_w = frame.shape[:2]
        detected_faces: List[Dict[str, Any]] = []

        # Downscale for inference if requested to achieve high frame rate
        if use_inference_scaling and self.inference_width > 0 and orig_w > self.inference_width:
            scale = self.inference_width / float(orig_w)
            inf_w = int(orig_w * scale)
            inf_h = int(orig_h * scale)
            inf_frame = cv2.resize(frame, (inf_w, inf_h), interpolation=cv2.INTER_LINEAR)
            scale_x = orig_w / float(inf_w)
            scale_y = orig_h / float(inf_h)
        else:
            inf_frame = frame
            scale_x, scale_y = 1.0, 1.0

        # 1. Primary: YOLO Detection
        if self.model is not None:
            try:
                results = self.model.predict(
                    source=inf_frame,
                    conf=self.conf_thresh,
                    verbose=False,
                    classes=[0]  # Detect person / face
                )

                for result in results:
                    boxes = result.boxes
                    if boxes is None:
                        continue
                    for box in boxes:
                        bx1, by1, bx2, by2 = map(float, box.xyxy[0].tolist())
                        conf = float(box.conf[0].item())
                        
                        # Rescale coordinates to original frame dimensions
                        x1 = int(round(bx1 * scale_x))
                        y1 = int(round(by1 * scale_y))
                        x2 = int(round(bx2 * scale_x))
                        y2 = int(round(by2 * scale_y))
                        
                        # Clamp bounding box inside image boundaries
                        x1, y1 = max(0, x1), max(0, y1)
                        x2, y2 = min(orig_w, x2), min(orig_h, y2)
                        
                        # For YOLO person detection, focus on upper head/face region if full body
                        box_h = y2 - y1
                        if box_h > 0.4 * orig_h:
                            y2 = min(orig_h, y1 + int(box_h * 0.45))

                        if (x2 - x1) >= 20 and (y2 - y1) >= 20:
                            detected_faces.append({
                                "bbox": [x1, y1, x2, y2],
                                "confidence": round(conf, 2)
                            })

                res = {"faces": detected_faces, "count": len(detected_faces)}
                self._last_detections = res
                return res
            except Exception as e:
                logger.error(f"Error during YOLO inference: {e}")

        # 2. Fallback: OpenCV Haar / YuNet Face Detection
        try:
            gray = cv2.cvtColor(inf_frame, cv2.COLOR_BGR2GRAY)
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            face_cascade = cv2.CascadeClassifier(cascade_path)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

            for (x, y, fw, fh) in faces:
                x1 = int(round(x * scale_x))
                y1 = int(round(y * scale_y))
                x2 = int(round((x + fw) * scale_x))
                y2 = int(round((y + fh) * scale_y))
                detected_faces.append({
                    "bbox": [max(0, x1), max(0, y1), min(orig_w, x2), min(orig_h, y2)],
                    "confidence": 0.85
                })
        except Exception as e:
            logger.error(f"Fallback face detector error: {e}")

        res = {"faces": detected_faces, "count": len(detected_faces)}
        self._last_detections = res
        return res

    def get_last_detections(self) -> Dict[str, Any]:
        """Return the most recent detection result without running new inference."""
        return self._last_detections

    def draw_detections(
        self,
        frame: np.ndarray,
        detections: Dict[str, Any],
        color: Tuple[int, int, int] = (0, 210, 255),  # Cyan
        label_prefix: str = "Face"
    ) -> np.ndarray:
        """
        Draw aesthetic bounding boxes and confidence badges on the frame.
        
        Args:
            frame: Target BGR frame to draw on
            detections: Output from detect_faces()
            color: Box BGR color tuple
            label_prefix: Label text prefix
            
        Returns:
            Annotated BGR frame
        """
        if frame is None:
            return frame

        annotated = frame.copy()
        faces = detections.get("faces", [])

        for i, face in enumerate(faces):
            x1, y1, x2, y2 = face["bbox"]
            conf = face.get("confidence", 0.0)
            identity = face.get("identity", {})
            id_status = identity.get("status")
            id_name = identity.get("name")
            id_conf = identity.get("confidence", 0.0)

            # Dynamic color coding based on 3-tier identity authorization
            if id_status == "AUTHORIZED":
                box_color = (0, 230, 118)   # Bright Emerald Green
                corner_color = (255, 255, 255)
                label = f"AUTHORIZED: {id_name or 'User'} ({int(id_conf * 100)}%)"
            elif id_status == "UNCERTAIN":
                box_color = (0, 165, 255)   # Amber / Orange
                corner_color = (255, 200, 0)
                label = f"UNCERTAIN ({int(id_conf * 100)}%)"
            elif id_status == "UNKNOWN":
                box_color = (50, 50, 240)   # Alert Red
                corner_color = (0, 165, 255) # Orange accent
                label = "UNKNOWN VIEWER"
            elif id_status == "NO_REGISTERED_USERS":
                box_color = (148, 163, 184) # Slate Gray
                corner_color = (200, 200, 200)
                label = f"{label_prefix} #{i+1}: Unenrolled"
            else:
                box_color = color            # Default Cyan
                corner_color = (0, 255, 128)
                label = f"{label_prefix} #{i+1}: {int(conf * 100)}%"

            # Draw main bounding rectangle
            cv2.rectangle(annotated, (x1, y1), (x2, y2), box_color, 2, cv2.LINE_AA)

            # Corner accents for a modern HUD tech look
            corner_len = min(20, max(6, (x2 - x1) // 4), max(6, (y2 - y1) // 4))
            thickness = 3

            # Top-Left Corner
            cv2.line(annotated, (x1, y1), (x1 + corner_len, y1), corner_color, thickness)
            cv2.line(annotated, (x1, y1), (x1, y1 + corner_len), corner_color, thickness)

            # Top-Right Corner
            cv2.line(annotated, (x2, y1), (x2 - corner_len, y1), corner_color, thickness)
            cv2.line(annotated, (x2, y1), (x2, y1 + corner_len), corner_color, thickness)

            # Bottom-Left Corner
            cv2.line(annotated, (x1, y2), (x1 + corner_len, y2), corner_color, thickness)
            cv2.line(annotated, (x1, y2), (x1, y2 - corner_len), corner_color, thickness)

            # Bottom-Right Corner
            cv2.line(annotated, (x2, y2), (x2 - corner_len, y2), corner_color, thickness)
            cv2.line(annotated, (x2, y2), (x2, y2 - corner_len), corner_color, thickness)

            # Badge Label Background
            (text_w, text_h), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            
            badge_y1 = max(0, y1 - text_h - 8)
            badge_y2 = y1
            cv2.rectangle(annotated, (x1, badge_y1), (x1 + text_w + 10, badge_y2), (15, 23, 42), -1)
            cv2.rectangle(annotated, (x1, badge_y1), (x1 + text_w + 10, badge_y2), box_color, 1)

            # Label Text
            cv2.putText(
                annotated,
                label,
                (x1 + 5, badge_y2 - 4),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (241, 245, 249),
                1,
                cv2.LINE_AA
            )

        return annotated

    @staticmethod
    def extract_face_crop(frame: np.ndarray, bbox: List[int]) -> Optional[np.ndarray]:
        """
        Safely extract a cropped face image region for recognition.
        
        Args:
            frame: Original BGR frame
            bbox: [x1, y1, x2, y2]
            
        Returns:
            Cropped BGR face image, or None if invalid bbox
        """
        if frame is None or len(bbox) != 4:
            return None
            
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = bbox
        
        # Clamp bounds
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        
        if x2 <= x1 or y2 <= y1:
            return None
            
        return frame[y1:y2, x1:x2].copy()


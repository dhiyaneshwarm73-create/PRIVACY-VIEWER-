"""
Thread-Safe High-Performance Webcam Stream Module using OpenCV and PySide6 QThread.

Safely decouples hardware webcam acquisition and AI processing, discards stale buffered frames,
measures FPS and latency accurately, and communicates with the UI via Qt Signals.
"""

import queue
import threading
import time
from typing import Any, Dict, Optional
import cv2
import numpy as np
from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtGui import QImage

from app.ai.face_detection import FaceDetector
from app.ai.face_recognition import FaceRecognizer
from app.ai.gaze_tracking import GazeTracker
from app.utils.config import config
from app.utils.logger import setup_logger
from app.utils.performance import FPSTracker, LatencyTimer, PipelineProfiler

logger = setup_logger("CameraWorker")


class FrameCaptureThread(threading.Thread):
    """
    Dedicated lightweight capture thread that continuously reads from the hardware webcam
    and pushes to a bounded queue (maxsize=1) so outdated frames are discarded immediately.
    """
    def __init__(self, camera_index: int, width: int = 640, height: int = 480):
        super().__init__(daemon=True, name="WebcamCaptureThread")
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.running = False
        self.cap: Optional[cv2.VideoCapture] = None
        self.frame_queue: queue.Queue = queue.Queue(maxsize=1)
        self.fps_tracker = FPSTracker(buffer_size=30)
        self.capture_fps = 0.0
        self.open_success = False

    def open_camera(self) -> bool:
        """Initialize OpenCV camera capture with DirectShow fallback."""
        try:
            logger.info(f"Opening webcam (Index {self.camera_index})...")
            # Try DirectShow on Windows for fastest startup
            self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
            if not self.cap or not self.cap.isOpened():
                logger.warning("DirectShow capture failed, falling back to default OpenCV backend...")
                self.cap = cv2.VideoCapture(self.camera_index)

            if not self.cap or not self.cap.isOpened():
                logger.error(f"Cannot open webcam index {self.camera_index}.")
                self.open_success = False
                return False

            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.open_success = True
            return True
        except Exception as e:
            logger.error(f"Error opening camera device: {e}")
            self.open_success = False
            return False

    def run(self):
        self.running = True
        while self.running:
            if self.cap is None or not self.cap.isOpened():
                time.sleep(0.05)
                continue

            ret, frame = self.cap.read()
            if not ret or frame is None:
                time.sleep(0.02)
                continue

            self.capture_fps = self.fps_tracker.tick()

            # Discard any older unconsumed frame in bounded queue
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                pass

            # Push newest frame
            try:
                self.frame_queue.put_nowait(frame)
            except queue.Full:
                pass

    def get_latest_frame(self, timeout: float = 0.1) -> Optional[np.ndarray]:
        """Fetch the newest available frame."""
        try:
            return self.frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def stop(self):
        self.running = False
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception as e:
                logger.debug(f"Error releasing camera: {e}")
            self.cap = None


class CameraWorker(QThread):
    """
    Background worker thread for continuous frame processing:
    YOLO face detection, 3-tier face recognition, gaze estimation, HUD overlay,
    and real-time latency & FPS profiling.
    """
    frame_ready = Signal(QImage)
    fps_updated = Signal(float)
    latency_updated = Signal(float, float)      # (inference_latency_ms, total_latency_ms)
    faces_detected = Signal(int)
    identity_updated = Signal(str, str, float)  # (status, name, confidence)
    gaze_updated = Signal(str, float, float)     # (direction, yaw, confidence)
    status_changed = Signal(bool, str)          # (is_active, message)
    error_occurred = Signal(str)
    
    # Telemetry signal for PrivacyEngine
    telemetry_updated = Signal(dict)

    def __init__(self, camera_index: int = None, parent: QObject = None):
        super().__init__(parent)
        self.camera_index = camera_index if camera_index is not None else config.camera.camera_index
        self.running = False
        
        self.capture_thread: Optional[FrameCaptureThread] = None
        self.fps_tracker = FPSTracker(buffer_size=30)
        self.profiler = PipelineProfiler(history_size=20)
        
        self.face_detector = FaceDetector()
        self.face_recognizer = FaceRecognizer()
        self.gaze_tracker = GazeTracker()
        
        self.frame_count = 0
        self._cached_detections: Dict[str, Any] = {"faces": [], "count": 0}

    def run(self):
        """Thread execution loop."""
        self.capture_thread = FrameCaptureThread(
            camera_index=self.camera_index,
            width=config.camera.frame_width,
            height=config.camera.frame_height
        )
        
        if not self.capture_thread.open_camera():
            err_msg = f"Failed to open webcam (Index {self.camera_index}). Please verify device connection."
            logger.error(err_msg)
            self.error_occurred.emit(err_msg)
            self.status_changed.emit(False, "Camera Unavailable")
            return

        self.capture_thread.start()
        self.running = True
        logger.info("Webcam successfully opened and stream started.")
        self.status_changed.emit(True, "Camera Active")

        while self.running:
            loop_start = time.perf_counter()
            frame = self.capture_thread.get_latest_frame(timeout=0.08)
            if frame is None:
                if not self.running:
                    break
                continue

            self.frame_count += 1
            fps = self.fps_tracker.tick()
            self.fps_updated.emit(fps)

            # 1. Face Detection with Downscaled Inference & Frame Skipping
            skip_frames = config.detection.inference_skip_frames
            infer_start = time.perf_counter()
            
            if self.frame_count % skip_frames == 0 or self._cached_detections["count"] == 0:
                with LatencyTimer("detection") as det_timer:
                    detections = self.face_detector.detect_faces(frame, use_inference_scaling=True)
                self._cached_detections = detections
                self.profiler.record("detection", det_timer.elapsed_ms)
            else:
                detections = self._cached_detections

            num_faces = detections.get("count", 0)
            self.faces_detected.emit(num_faces)

            # 2. 3-Tier Face Recognition (DeepFace / Local Embeddings)
            primary_status = "NO_FACES"
            primary_name = "None"
            primary_conf = 0.0
            gaze_dir = "UNKNOWN"
            gaze_yaw = 0.0
            gaze_conf = 0.0
            gaze_res = {"direction": "UNKNOWN", "angles": {"yaw": 0.0}}

            if num_faces > 0:
                with LatencyTimer("recognition") as rec_timer:
                    enriched_faces = self.face_recognizer.process_frame_detections(frame, detections["faces"])
                detections["faces"] = enriched_faces
                self.profiler.record("recognition", rec_timer.elapsed_ms)

                # Primary face identity
                primary_face = enriched_faces[0]
                primary_id = primary_face.get("identity", {})
                primary_status = primary_id.get("status", "UNKNOWN")
                primary_name = primary_id.get("name", "Unknown Viewer")
                primary_conf = primary_id.get("confidence", 0.0)

                self.identity_updated.emit(primary_status, primary_name or "Unknown", primary_conf)

                # 3. Gaze & Head Pose Tracking on primary face
                with LatencyTimer("gaze") as gaze_timer:
                    primary_bbox = primary_face.get("bbox")
                    gaze_res = self.gaze_tracker.estimate_gaze(frame, primary_bbox)
                self.profiler.record("gaze", gaze_timer.elapsed_ms)

                gaze_dir = gaze_res.get("direction", "CENTER")
                gaze_yaw = gaze_res.get("angles", {}).get("yaw", 0.0)
                gaze_conf = gaze_res.get("confidence", 0.85)
                self.gaze_updated.emit(gaze_dir, gaze_yaw, gaze_conf)
            else:
                self.identity_updated.emit("NO_FACES", "None", 0.0)
                self.gaze_updated.emit("UNKNOWN", 0.0, 0.0)

            # Measure Inference & Total Latency
            infer_latency_ms = (time.perf_counter() - infer_start) * 1000.0
            total_latency_ms = (time.perf_counter() - loop_start) * 1000.0
            self.profiler.record("total_inference", infer_latency_ms)
            self.latency_updated.emit(round(infer_latency_ms, 1), round(total_latency_ms, 1))

            # Emit Telemetry snapshot for Privacy Engine
            telemetry = {
                "num_faces": num_faces,
                "faces": detections.get("faces", []),
                "primary_status": primary_status,
                "primary_name": primary_name,
                "primary_confidence": primary_conf,
                "gaze_direction": gaze_dir,
                "gaze_yaw": gaze_yaw,
                "fps": fps,
                "latency_ms": infer_latency_ms,
                "timestamp": time.time()
            }
            self.telemetry_updated.emit(telemetry)

            # 4. Annotate native frame with bounding boxes & HUD accents
            display_frame = self.face_detector.draw_detections(frame, detections)
            if num_faces > 0:
                display_frame = self.gaze_tracker.draw_gaze_hud(display_frame, gaze_res, primary_bbox)

            # Convert BGR (OpenCV) to RGB for Qt rendering
            rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            
            # Create Qt QImage
            qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()
            self.frame_ready.emit(qt_image)

        # Teardown
        if self.capture_thread is not None:
            self.capture_thread.stop()
            self.capture_thread.join(timeout=1.0)
            self.capture_thread = None
            
        logger.info("Webcam stream stopped and hardware resources released.")
        self.status_changed.emit(False, "Camera Stopped")

    def stop(self):
        """Signal the worker and capture thread to terminate safely."""
        self.running = False
        if self.capture_thread is not None:
            self.capture_thread.stop()
        self.wait(1500)


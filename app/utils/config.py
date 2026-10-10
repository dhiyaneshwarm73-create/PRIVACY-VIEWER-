"""
Central Configuration Management for AI Privacy Viewer.

This module centralizes all configurable application parameters, paths,
and thresholds to ensure consistency and avoid hardcoded values across modules.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path


# Project Root Directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass
class CameraConfig:
    """Webcam capture configuration."""
    camera_index: int = 0
    frame_width: int = 640
    frame_height: int = 480
    fps_target: int = 30
    auto_reconnect: bool = True
    reconnect_delay_sec: float = 2.0


@dataclass
class DetectionConfig:
    """YOLO Face Detection configuration."""
    model_name: str = "yolov8n-face.pt"
    confidence_threshold: float = 0.50
    nms_iou_threshold: float = 0.45
    input_size: int = 640
    use_gpu_if_available: bool = True


@dataclass
class RecognitionConfig:
    """DeepFace Face Recognition configuration."""
    model_name: str = "Facenet512"  # Fast, accurate, lightweight
    distance_metric: str = "cosine"
    distance_threshold: float = 0.40
    recognition_interval_frames: int = 5  # Run recognition every N frames for speed
    cache_duration_sec: float = 2.0       # Cache identity results to avoid heavy recomputation


@dataclass
class GazeConfig:
    """MediaPipe Gaze / Eye / Head Tracking configuration."""
    confidence_threshold: float = 0.50
    yaw_threshold_degrees: float = 25.0    # Angle beyond which user is looking LEFT/RIGHT/AWAY
    pitch_threshold_degrees: float = 20.0  # Angle beyond which user is looking UP/DOWN/AWAY
    smooth_factor: float = 0.6             # Exponential moving average filter for head pose


@dataclass
class PrivacyEngineConfig:
    """Privacy Decision Engine & Debouncing configuration."""
    # Number of consecutive frames an unknown person must be seen before triggering privacy mode
    consecutive_unknown_frames: int = 4
    
    # Frames required to confirm multiple people
    consecutive_multiple_faces_frames: int = 3
    
    # Number of seconds the authorized user looks away before triggering privacy mode
    look_away_delay_sec: float = 3.0
    
    # Seconds without threat required before returning back to NORMAL mode (prevents screen flicker)
    recovery_delay_sec: float = 1.0


@dataclass
class StorageConfig:
    """File and Directory paths."""
    data_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "data")
    authorized_faces_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "authorized_faces")
    models_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "models")
    logs_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "logs")
    db_path: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "privacy_viewer.db")

    def ensure_directories_exist(self) -> None:
        """Create necessary directories if they do not exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.authorized_faces_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)


@dataclass
class AppConfig:
    """Global Application Configuration."""
    app_name: str = "AI Privacy Viewer"
    version: str = "0.1.0"
    debug_mode: bool = True
    
    # Nested configs
    camera: CameraConfig = field(default_factory=CameraConfig)
    detection: DetectionConfig = field(default_factory=DetectionConfig)
    recognition: RecognitionConfig = field(default_factory=RecognitionConfig)
    gaze: GazeConfig = field(default_factory=GazeConfig)
    privacy: PrivacyEngineConfig = field(default_factory=PrivacyEngineConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)


# Global singleton instance for easy import
config = AppConfig()
config.storage.ensure_directories_exist()

"""
Main Dashboard View for AI Privacy Viewer.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.ui.widgets import MetricCard, StatusBadge, VideoPreviewWidget


class DashboardView(QWidget):
    """
    Main monitoring dashboard displaying live camera feed, AI pipeline status,
    processing latency, and real-time privacy security metrics.
    """
    start_camera_requested = Signal()
    stop_camera_requested = Signal()
    toggle_privacy_shield_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_fps = 0.0
        self.current_latency_ms = 0.0
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # 1. Top Metrics KPI Row
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(16)

        self.card_fps = MetricCard("Performance", "0.0 FPS", "Latency: -- ms", "⚡")
        self.card_faces = MetricCard("Faces Detected", "0", "Visible in frame", "👥")
        self.card_identity = MetricCard("Identity", "None", "Authorization state", "👤")
        self.card_gaze = MetricCard("Gaze Direction", "CENTER", "Estimated orientation", "👁️")

        metrics_layout.addWidget(self.card_fps)
        metrics_layout.addWidget(self.card_faces)
        metrics_layout.addWidget(self.card_identity)
        metrics_layout.addWidget(self.card_gaze)

        main_layout.addLayout(metrics_layout)

        # 2. Main Content Split (Left: Video Preview, Right: Pipeline & Controls)
        content_split = QHBoxLayout()
        content_split.setSpacing(20)

        # --- Left: Camera Preview Container ---
        preview_container = QVBoxLayout()
        preview_container.setSpacing(10)
        
        self.video_preview = VideoPreviewWidget()
        preview_container.addWidget(self.video_preview, stretch=1)

        # Quick Preview Footer Controls
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(12)

        self.btn_start = QPushButton("▶  Start Camera")
        self.btn_start.setObjectName("PrimaryButton")
        self.btn_start.clicked.connect(self.start_camera_requested.emit)

        self.btn_stop = QPushButton("⏹  Stop Camera")
        self.btn_stop.setObjectName("DangerButton")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_camera_requested.emit)

        self.btn_test_shield = QPushButton("🛡️  Test Screen Shield")
        self.btn_test_shield.clicked.connect(self.toggle_privacy_shield_requested.emit)

        controls_layout.addWidget(self.btn_start)
        controls_layout.addWidget(self.btn_stop)
        controls_layout.addStretch()
        controls_layout.addWidget(self.btn_test_shield)

        preview_container.addLayout(controls_layout)
        content_split.addLayout(preview_container, stretch=3)

        # --- Right: Pipeline Status & Controls Panel ---
        right_panel = QFrame()
        right_panel.setProperty("class", "CardWidget")
        right_panel.setMinimumWidth(300)
        right_panel.setMaximumWidth(340)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(18, 18, 18, 18)
        right_layout.setSpacing(14)

        panel_title = QLabel("PIPELINE & SHIELD STATUS")
        panel_title.setProperty("class", "CardTitle")
        right_layout.addWidget(panel_title)

        # Status Badges for each subsystem
        self.badge_camera = StatusBadge("Webcam Stream", "OFFLINE", "neutral")
        self.badge_detection = StatusBadge("Face Detection", "READY (YOLOv8)", "info")
        self.badge_recognition = StatusBadge("3-Tier Recognition", "STANDBY (Facenet)", "info")
        self.badge_gaze = StatusBadge("Gaze Tracking", "STANDBY (MediaPipe)", "info")
        self.badge_privacy = StatusBadge("Desktop Shield", "NORMAL (Safe)", "success")

        right_layout.addWidget(self.badge_camera)
        right_layout.addWidget(self.badge_detection)
        right_layout.addWidget(self.badge_recognition)
        right_layout.addWidget(self.badge_gaze)
        right_layout.addWidget(self.badge_privacy)

        right_layout.addStretch()

        # System Info Box
        info_box = QFrame()
        info_box.setStyleSheet("background-color: #0b0f19; border-radius: 8px; padding: 10px;")
        info_layout = QVBoxLayout(info_box)
        info_layout.setSpacing(6)
        
        info_title = QLabel("ACTIVE SECURITY POLICY")
        info_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #38bdf8;")
        info_desc = QLabel("• Screen overlay on unknown viewer\n• Shoulder-surfing protection\n• 3-tier authorized/uncertain logic\n• 100% On-device local biometrics")
        info_desc.setStyleSheet("font-size: 11px; color: #94a3b8; line-height: 140%;")
        
        info_layout.addWidget(info_title)
        info_layout.addWidget(info_desc)
        right_layout.addWidget(info_box)

        content_split.addWidget(right_panel, stretch=1)
        main_layout.addLayout(content_split, stretch=1)

    def update_fps(self, fps: float):
        """Update FPS display."""
        self.current_fps = fps
        self.card_fps.set_value(f"{fps:.1f} FPS", f"Latency: {self.current_latency_ms:.1f} ms")

    def update_latency(self, infer_latency_ms: float, total_latency_ms: float):
        """Update latency metric."""
        self.current_latency_ms = infer_latency_ms
        self.card_fps.set_value(f"{self.current_fps:.1f} FPS", f"AI Latency: {infer_latency_ms:.1f} ms")

    def set_camera_running(self, running: bool):
        """Update button states and badges when camera starts or stops."""
        self.btn_start.setEnabled(not running)
        self.btn_stop.setEnabled(running)
        self.video_preview.set_camera_active(running)
        
        if running:
            self.badge_camera.set_status("ACTIVE (30 FPS)", "success")
        else:
            self.badge_camera.set_status("OFFLINE", "neutral")
            self.card_fps.set_value("0.0 FPS", "Latency: -- ms")
            self.card_faces.set_value("0")
            self.card_identity.set_value("None")
            self.card_gaze.set_value("CENTER")


"""
System Settings and Threshold Configuration View.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.utils.config import config
from app.utils.logger import setup_logger

logger = setup_logger("SettingsView")


class SettingsView(QWidget):
    """
    User settings view for configuring camera, AI thresholds, downscaling,
    and screen privacy overlay parameters.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        # 1. Header
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)
        
        title = QLabel("System Settings & Thresholds")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #f8fafc;")
        
        subtitle = QLabel("Tune detection sensitivity, 3-tier recognition thresholds, and screen privacy overlay behavior.")
        subtitle.setStyleSheet("font-size: 13px; color: #94a3b8;")
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        main_layout.addLayout(header_layout)

        # Scrollable container for settings cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        scroll_content = QWidget()
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setSpacing(16)

        # Card 1: Camera Hardware & Video Stream
        cam_card = self._create_card("CAMERA HARDWARE SETTINGS")
        cam_layout = QGridLayout()
        cam_layout.setSpacing(12)

        cam_layout.addWidget(QLabel("Camera Device Index:"), 0, 0)
        self.spin_cam_idx = QSpinBox()
        self.spin_cam_idx.setRange(0, 10)
        self.spin_cam_idx.setValue(config.camera.camera_index)
        cam_layout.addWidget(self.spin_cam_idx, 0, 1)

        cam_layout.addWidget(QLabel("Display Capture Resolution:"), 1, 0)
        self.combo_res = QComboBox()
        self.combo_res.addItems(["640 x 480 (Recommended - Fast)", "1280 x 720 (HD)", "1920 x 1080 (Full HD)"])
        cam_layout.addWidget(self.combo_res, 1, 1)

        cam_card.layout().addLayout(cam_layout)
        content_layout.addWidget(cam_card)

        # Card 2: AI Sensitivity, Inference Downscaling & 3-Tier Recognition
        ai_card = self._create_card("AI SENSITIVITY & 3-TIER RECOGNITION")
        ai_layout = QGridLayout()
        ai_layout.setSpacing(12)

        ai_layout.addWidget(QLabel("YOLO Detection Confidence:"), 0, 0)
        self.spin_yolo_conf = QDoubleSpinBox()
        self.spin_yolo_conf.setRange(0.10, 0.95)
        self.spin_yolo_conf.setSingleStep(0.05)
        self.spin_yolo_conf.setValue(config.detection.confidence_threshold)
        ai_layout.addWidget(self.spin_yolo_conf, 0, 1)

        ai_layout.addWidget(QLabel("Inference Downscaled Width (px):"), 1, 0)
        self.spin_inf_width = QSpinBox()
        self.spin_inf_width.setRange(160, 640)
        self.spin_inf_width.setSingleStep(32)
        self.spin_inf_width.setValue(config.detection.inference_width)
        ai_layout.addWidget(self.spin_inf_width, 1, 1)

        ai_layout.addWidget(QLabel("Authorized Match Distance Threshold:"), 2, 0)
        self.spin_rec_thresh = QDoubleSpinBox()
        self.spin_rec_thresh.setRange(0.10, 0.60)
        self.spin_rec_thresh.setSingleStep(0.02)
        self.spin_rec_thresh.setValue(config.recognition.distance_threshold)
        ai_layout.addWidget(self.spin_rec_thresh, 2, 1)

        ai_layout.addWidget(QLabel("Uncertain Identity Margin Threshold:"), 3, 0)
        self.spin_uncert_thresh = QDoubleSpinBox()
        self.spin_uncert_thresh.setRange(0.30, 0.80)
        self.spin_uncert_thresh.setSingleStep(0.02)
        self.spin_uncert_thresh.setValue(config.recognition.uncertain_threshold)
        ai_layout.addWidget(self.spin_uncert_thresh, 3, 1)

        ai_layout.addWidget(QLabel("Recognition Interval (Frames):"), 4, 0)
        self.spin_rec_interval = QSpinBox()
        self.spin_rec_interval.setRange(1, 30)
        self.spin_rec_interval.setValue(config.recognition.recognition_interval_frames)
        ai_layout.addWidget(self.spin_rec_interval, 4, 1)

        ai_card.layout().addLayout(ai_layout)
        content_layout.addWidget(ai_card)

        # Card 3: Screen-Wide Privacy Shield & Debouncing
        priv_card = self._create_card("SCREEN PRIVACY OVERLAY & THREAT DEBOUNCING")
        priv_layout = QGridLayout()
        priv_layout.setSpacing(12)

        self.chk_enable_overlay = QCheckBox("Enable Full-Screen Desktop Privacy Overlay")
        self.chk_enable_overlay.setChecked(config.privacy.enable_overlay)
        self.chk_enable_overlay.setStyleSheet("color: #f8fafc; font-weight: 600;")
        priv_layout.addWidget(self.chk_enable_overlay, 0, 0, 1, 2)

        self.chk_blurred_bg = QCheckBox("Use Blurred Desktop Snapshot as Overlay Background")
        self.chk_blurred_bg.setChecked(config.privacy.use_blurred_background)
        self.chk_blurred_bg.setStyleSheet("color: #cbd5e1;")
        priv_layout.addWidget(self.chk_blurred_bg, 1, 0, 1, 2)

        priv_layout.addWidget(QLabel("Unknown Face Trigger (Frames):"), 2, 0)
        self.spin_unknown_frames = QSpinBox()
        self.spin_unknown_frames.setRange(1, 20)
        self.spin_unknown_frames.setValue(config.privacy.consecutive_unknown_frames)
        priv_layout.addWidget(self.spin_unknown_frames, 2, 1)

        priv_layout.addWidget(QLabel("Multiple Faces / Crowd Trigger (Frames):"), 3, 0)
        self.spin_crowd_frames = QSpinBox()
        self.spin_crowd_frames.setRange(1, 15)
        self.spin_crowd_frames.setValue(config.privacy.consecutive_multiple_faces_frames)
        priv_layout.addWidget(self.spin_crowd_frames, 3, 1)

        self.chk_look_away = QCheckBox("Enable Look-Away Protection")
        self.chk_look_away.setChecked(config.privacy.enable_look_away)
        self.chk_look_away.setStyleSheet("color: #cbd5e1;")
        priv_layout.addWidget(self.chk_look_away, 4, 0)

        self.spin_look_away = QDoubleSpinBox()
        self.spin_look_away.setRange(1.0, 15.0)
        self.spin_look_away.setSingleStep(0.5)
        self.spin_look_away.setValue(config.privacy.look_away_delay_sec)
        priv_layout.addWidget(self.spin_look_away, 4, 1)

        priv_layout.addWidget(QLabel("Threat Recovery Delay (Sec):"), 5, 0)
        self.spin_recovery = QDoubleSpinBox()
        self.spin_recovery.setRange(0.5, 10.0)
        self.spin_recovery.setSingleStep(0.5)
        self.spin_recovery.setValue(config.privacy.recovery_delay_sec)
        priv_layout.addWidget(self.spin_recovery, 5, 1)

        priv_card.layout().addLayout(priv_layout)
        content_layout.addWidget(priv_card)

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll, stretch=1)

        # Footer Actions
        footer = QHBoxLayout()
        footer.setSpacing(12)

        self.btn_reset = QPushButton("Reset Defaults")
        self.btn_reset.clicked.connect(self.reset_defaults)

        self.btn_save = QPushButton("💾 Save Settings")
        self.btn_save.setObjectName("PrimaryButton")
        self.btn_save.clicked.connect(self.save_settings)

        footer.addStretch()
        footer.addWidget(self.btn_reset)
        footer.addWidget(self.btn_save)
        main_layout.addLayout(footer)

    def _create_card(self, title: str) -> QFrame:
        card = QFrame()
        card.setProperty("class", "CardWidget")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)
        
        lbl_title = QLabel(title)
        lbl_title.setProperty("class", "CardTitle")
        layout.addWidget(lbl_title)
        return card

    def save_settings(self):
        """Update live config object with user-selected values."""
        config.camera.camera_index = self.spin_cam_idx.value()
        config.detection.confidence_threshold = self.spin_yolo_conf.value()
        config.detection.inference_width = self.spin_inf_width.value()
        config.recognition.distance_threshold = self.spin_rec_thresh.value()
        config.recognition.uncertain_threshold = self.spin_uncert_thresh.value()
        config.recognition.recognition_interval_frames = self.spin_rec_interval.value()
        
        config.privacy.enable_overlay = self.chk_enable_overlay.isChecked()
        config.privacy.use_blurred_background = self.chk_blurred_bg.isChecked()
        config.privacy.consecutive_unknown_frames = self.spin_unknown_frames.value()
        config.privacy.consecutive_multiple_faces_frames = self.spin_crowd_frames.value()
        config.privacy.enable_look_away = self.chk_look_away.isChecked()
        config.privacy.look_away_delay_sec = self.spin_look_away.value()
        config.privacy.recovery_delay_sec = self.spin_recovery.value()

        logger.info("Settings saved successfully.")
        QMessageBox.information(self, "Settings Saved", "Configuration parameters updated successfully.")

    def reset_defaults(self):
        """Reset values back to defaults."""
        self.spin_cam_idx.setValue(0)
        self.spin_yolo_conf.setValue(0.50)
        self.spin_inf_width.setValue(320)
        self.spin_rec_thresh.setValue(0.38)
        self.spin_uncert_thresh.setValue(0.52)
        self.spin_rec_interval.setValue(6)
        
        self.chk_enable_overlay.setChecked(True)
        self.chk_blurred_bg.setChecked(True)
        self.spin_unknown_frames.setValue(3)
        self.spin_crowd_frames.setValue(2)
        self.chk_look_away.setChecked(False)
        self.spin_look_away.setValue(3.0)
        self.spin_recovery.setValue(1.2)
        logger.info("Settings reset to defaults.")


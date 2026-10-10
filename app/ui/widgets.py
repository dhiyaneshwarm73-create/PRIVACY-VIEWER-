"""
Reusable UI Widgets for AI Privacy Viewer.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPaintEvent, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)


class StatusBadge(QFrame):
    """
    Status indicator badge with a glowing colored dot.
    Colors: 'success' (green), 'warning' (amber), 'danger' (red), 'info' (cyan), 'neutral' (gray)
    """
    def __init__(self, title: str, status_text: str = "OFFLINE", status_type: str = "neutral", parent=None):
        super().__init__(parent)
        self.setObjectName("StatusBadge")
        self.setProperty("class", "CardWidget")
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(12, 8, 12, 8)
        self.layout.setSpacing(10)
        
        # Indicator Dot
        self.dot_label = QLabel("●")
        self.dot_label.setFont(QFont("Segoe UI", 12))
        
        # Text layout
        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)
        
        self.title_label = QLabel(title)
        self.title_label.setProperty("class", "CardTitle")
        
        self.status_label = QLabel(status_text)
        self.status_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        
        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.status_label)
        
        self.layout.addWidget(self.dot_label)
        self.layout.addLayout(text_layout)
        self.layout.addStretch()
        
        self.set_status(status_text, status_type)

    def set_status(self, text: str, status_type: str = "neutral"):
        """Update badge text and color theme."""
        self.status_label.setText(text)
        
        color_map = {
            "success": "#10b981",  # Emerald Green
            "warning": "#f59e0b",  # Amber
            "danger": "#ef4444",   # Crimson Red
            "info": "#38bdf8",     # Cyan Blue
            "neutral": "#64748b",  # Slate Gray
        }
        color = color_map.get(status_type, "#64748b")
        self.dot_label.setStyleSheet(f"color: {color}; font-size: 14px;")
        self.status_label.setStyleSheet(f"color: {color};")


class MetricCard(QFrame):
    """
    Dashboard KPI card displaying a prominent value, title, and auxiliary info.
    """
    def __init__(self, title: str, initial_value: str = "--", subtext: str = "", icon: str = "", parent=None):
        super().__init__(parent)
        self.setProperty("class", "CardWidget")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)
        
        header_layout = QHBoxLayout()
        self.title_label = QLabel(title)
        self.title_label.setProperty("class", "CardTitle")
        header_layout.addWidget(self.title_label)
        
        if icon:
            self.icon_label = QLabel(icon)
            self.icon_label.setStyleSheet("font-size: 14px;")
            header_layout.addStretch()
            header_layout.addWidget(self.icon_label)
            
        layout.addLayout(header_layout)
        
        self.value_label = QLabel(initial_value)
        self.value_label.setProperty("class", "CardValue")
        layout.addWidget(self.value_label)
        
        self.subtext_label = QLabel(subtext)
        self.subtext_label.setProperty("class", "CardSubtext")
        layout.addWidget(self.subtext_label)

    def set_value(self, value: str, subtext: str = None):
        """Update metric value and optional subtext."""
        self.value_label.setText(str(value))
        if subtext is not None:
            self.subtext_label.setText(subtext)


class VideoPreviewWidget(QFrame):
    """
    Webcam video display area with placeholder and HUD overlay badges.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("VideoPreviewContainer")
        self.setMinimumSize(640, 420)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Stacked layout for video frame and placeholder
        self.stacked_layout = QStackedLayout(self)
        self.stacked_layout.setStackingMode(QStackedLayout.StackAll)
        
        # 1. Video Label (Base Layer)
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: #000000; border-radius: 10px;")
        self.video_label.setScaledContents(False)
        self.stacked_layout.addWidget(self.video_label)
        
        # 2. Placeholder Widget (Shown when camera is offline)
        self.placeholder_widget = QWidget()
        placeholder_layout = QVBoxLayout(self.placeholder_widget)
        placeholder_layout.setAlignment(Qt.AlignCenter)
        placeholder_layout.setSpacing(12)
        
        cam_icon = QLabel("📷")
        cam_icon.setAlignment(Qt.AlignCenter)
        cam_icon.setStyleSheet("font-size: 48px; color: #475569;")
        
        self.placeholder_title = QLabel("Camera Feed Inactive")
        self.placeholder_title.setObjectName("VideoPlaceholderLabel")
        self.placeholder_title.setAlignment(Qt.AlignCenter)
        self.placeholder_title.setStyleSheet("font-size: 16px; font-weight: 600; color: #94a3b8;")
        
        self.placeholder_subtitle = QLabel("Click 'Start Camera' below to initialize local webcam capture")
        self.placeholder_subtitle.setAlignment(Qt.AlignCenter)
        self.placeholder_subtitle.setStyleSheet("font-size: 12px; color: #64748b;")
        
        placeholder_layout.addWidget(cam_icon)
        placeholder_layout.addWidget(self.placeholder_title)
        placeholder_layout.addWidget(self.placeholder_subtitle)
        
        self.stacked_layout.addWidget(self.placeholder_widget)
        
        # 3. Privacy Shield Overlay (Shown during privacy breach)
        self.shield_overlay = QWidget()
        self.shield_overlay.setStyleSheet("""
            background-color: rgba(15, 23, 42, 0.95);
            border: 3px solid #ef4444;
            border-radius: 10px;
        """)
        shield_layout = QVBoxLayout(self.shield_overlay)
        shield_layout.setAlignment(Qt.AlignCenter)
        shield_layout.setSpacing(10)
        
        shield_icon = QLabel("🛡️⚠️")
        shield_icon.setAlignment(Qt.AlignCenter)
        shield_icon.setStyleSheet("font-size: 54px;")
        
        shield_title = QLabel("PRIVACY SHIELD ACTIVE")
        shield_title.setAlignment(Qt.AlignCenter)
        shield_title.setStyleSheet("font-size: 22px; font-weight: 800; color: #ef4444; letter-spacing: 1px;")
        
        self.shield_reason = QLabel("Unauthorized viewer detected near your screen")
        self.shield_reason.setAlignment(Qt.AlignCenter)
        self.shield_reason.setStyleSheet("font-size: 14px; color: #fca5a5; font-weight: 500;")
        
        shield_layout.addWidget(shield_icon)
        shield_layout.addWidget(shield_title)
        shield_layout.addWidget(self.shield_reason)
        
        self.stacked_layout.addWidget(self.shield_overlay)
        self.shield_overlay.setVisible(False)
        
        self.set_camera_active(False)

    def set_camera_active(self, active: bool):
        """Toggle between placeholder and active video."""
        self.placeholder_widget.setVisible(not active)
        if not active:
            self.video_label.clear()
            self.shield_overlay.setVisible(False)

    def set_privacy_shield(self, active: bool, reason: str = "Unauthorized viewer detected"):
        """Show or hide the visual privacy shield overlay."""
        self.shield_reason.setText(reason)
        self.shield_overlay.setVisible(active)

    def update_frame(self, q_pixmap: QPixmap):
        """Render a new video frame scaled to preserve aspect ratio."""
        if not self.placeholder_widget.isHidden():
            self.placeholder_widget.setVisible(False)
            
        scaled_pixmap = q_pixmap.scaled(
            self.video_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.video_label.setPixmap(scaled_pixmap)

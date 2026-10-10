"""
Windows-Compatible Screen-Wide Privacy Overlay.

Provides a full-screen, always-on-top protective privacy shield over the Windows desktop.
Supports immediate high-contrast opaque protection, optional one-shot blurred desktop snapshot,
recursion prevention, and safe owner dismissal.
"""

from typing import Optional
import cv2
import numpy as np
from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QGuiApplication,
    QImage,
    QPainter,
    QPaintEvent,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.utils.config import config
from app.utils.logger import setup_logger

logger = setup_logger("ScreenPrivacyOverlay")


class ScreenPrivacyOverlay(QWidget):
    """
    Top-level frameless, always-on-top desktop privacy screen.
    """
    shield_dismissed = Signal(str)  # (dismiss_reason)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_active = False
        self.current_reason = "Unauthorized viewer detected"
        self.background_pixmap: Optional[QPixmap] = None
        self._capturing_screen = False

        self.init_window_flags()
        self.init_ui()

    def init_window_flags(self):
        """Configure window to stay on top and cover the full display."""
        self.setWindowFlags(
            Qt.Window |
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.SubWindow
        )
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WA_DeleteOnClose, False)

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setAlignment(Qt.AlignCenter)

        # Central Modal Alert Container
        self.alert_card = QFrame(self)
        self.alert_card.setFixedSize(540, 360)
        self.alert_card.setStyleSheet("""
            QFrame {
                background-color: #0f172a;
                border: 2px solid #ef4444;
                border-radius: 16px;
            }
        """)

        card_layout = QVBoxLayout(self.alert_card)
        card_layout.setContentsMargins(32, 28, 32, 28)
        card_layout.setSpacing(14)
        card_layout.setAlignment(Qt.AlignCenter)

        # 1. Warning Icon & Glow
        icon_lbl = QLabel("🛡️ ⚠️", self.alert_card)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 46px; border: none; background: transparent;")
        card_layout.addWidget(icon_lbl)

        # 2. Alert Title
        title_lbl = QLabel("SCREEN PRIVACY SHIELD ACTIVE", self.alert_card)
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setStyleSheet("""
            font-size: 20px;
            font-weight: 800;
            color: #ef4444;
            letter-spacing: 1.5px;
            border: none;
            background: transparent;
        """)
        card_layout.addWidget(title_lbl)

        # 3. Dynamic Threat Reason
        self.lbl_reason = QLabel(self.current_reason, self.alert_card)
        self.lbl_reason.setAlignment(Qt.AlignCenter)
        self.lbl_reason.setWordWrap(True)
        self.lbl_reason.setStyleSheet("""
            font-size: 14px;
            font-weight: 600;
            color: #fca5a5;
            border: none;
            background: transparent;
        """)
        card_layout.addWidget(self.lbl_reason)

        # 4. Instruction Subtext
        subtext = QLabel(
            "Your desktop content has been protected from shoulder-surfing.\n"
            "Look back at the camera to restore automatically, or dismiss below.",
            self.alert_card
        )
        subtext.setAlignment(Qt.AlignCenter)
        subtext.setStyleSheet("""
            font-size: 12px;
            color: #94a3b8;
            border: none;
            background: transparent;
            line-height: 140%;
        """)
        card_layout.addWidget(subtext)

        card_layout.addSpacing(6)

        # 5. Safe Dismiss Button
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.setAlignment(Qt.AlignCenter)

        self.btn_dismiss = QPushButton("🔓 Dismiss Shield (Esc)", self.alert_card)
        self.btn_dismiss.setFixedHeight(42)
        self.btn_dismiss.setMinimumWidth(200)
        self.btn_dismiss.setCursor(Qt.PointingHandCursor)
        self.btn_dismiss.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: #ffffff;
                font-size: 13px;
                font-weight: 700;
                border-radius: 8px;
                border: 1px solid #dc2626;
                padding: 8px 18px;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
            QPushButton:pressed {
                background-color: #b91c1c;
            }
        """)
        self.btn_dismiss.clicked.connect(self.dismiss_by_user)
        btn_layout.addWidget(self.btn_dismiss)

        card_layout.addLayout(btn_layout)
        root_layout.addWidget(self.alert_card)

    def _capture_blurred_desktop(self) -> Optional[QPixmap]:
        """
        Safely capture a one-shot screenshot of the desktop and apply Gaussian blur.
        Prevents recursive self-capture by capturing strictly before the overlay is visible.
        """
        if self._capturing_screen:
            return None

        self._capturing_screen = True
        try:
            primary_screen = QGuiApplication.primaryScreen()
            if primary_screen is None:
                return None

            # Capture desktop
            screenshot = primary_screen.grabWindow(0)
            if screenshot.isNull():
                return None

            # Convert QPixmap to OpenCV BGR image for high-speed blur
            qimg = screenshot.toImage().convertToFormat(QImage.Format_RGB888)
            w, h = qimg.width(), qimg.height()
            ptr = qimg.bits()
            arr = np.frombuffer(ptr, dtype=np.uint8).reshape((h, w, 3))

            # Fast downscale-blur-upscale technique for silky smooth 60fps blur
            small = cv2.resize(arr, (w // 4, h // 4), interpolation=cv2.INTER_LINEAR)
            blurred_small = cv2.GaussianBlur(small, (35, 35), 18)
            blurred = cv2.resize(blurred_small, (w, h), interpolation=cv2.INTER_LINEAR)

            # Darken blurred image for contrast
            darkened = cv2.addWeighted(blurred, 0.45, np.zeros_like(blurred), 0.55, 0)

            # Convert back to QPixmap
            h_b, w_b, ch = darkened.shape
            bytes_per_line = ch * w_b
            blurred_qimg = QImage(darkened.data, w_b, h_b, bytes_per_line, QImage.Format_RGB888)
            return QPixmap.fromImage(blurred_qimg)
        except Exception as e:
            logger.warning(f"Failed to capture blurred desktop background: {e}")
            return None
        finally:
            self._capturing_screen = False

    def activate_shield(self, reason: str = "Unauthorized viewer detected"):
        """Show the screen-wide privacy overlay across the primary display."""
        if self.is_active:
            self.lbl_reason.setText(reason)
            return

        self.current_reason = reason
        self.lbl_reason.setText(reason)
        self.is_active = True

        # Position window over entire primary screen
        primary_screen = QGuiApplication.primaryScreen()
        if primary_screen:
            geom = primary_screen.geometry()
            self.setGeometry(geom)

        # Optional blurred snapshot (captured BEFORE showing overlay window)
        if config.privacy.use_blurred_background:
            self.background_pixmap = self._capture_blurred_desktop()
        else:
            self.background_pixmap = None

        self.showFullScreen()
        self.raise_()
        self.activateWindow()
        logger.info(f"Screen Privacy Shield ACTIVATED ({reason}).")

    def deactivate_shield(self):
        """Hide and dismiss the privacy overlay."""
        if not self.is_active:
            return

        self.is_active = False
        self.background_pixmap = None
        self.hide()
        logger.info("Screen Privacy Shield DEACTIVATED.")

    def dismiss_by_user(self):
        """Safe manual dismissal triggered by owner click or keypress."""
        self.deactivate_shield()
        self.shield_dismissed.emit("Manual Owner Dismissal")

    def keyPressEvent(self, event):
        """Allow owner to safely dismiss shield using Escape key."""
        if event.key() == Qt.Key_Escape:
            self.dismiss_by_user()
            event.accept()
        else:
            super().keyPressEvent(event)

    def paintEvent(self, event: QPaintEvent):
        """Draw background (either blurred desktop or sleek dark privacy gradient)."""
        painter = QPainter(self)
        if self.background_pixmap is not None and not self.background_pixmap.isNull():
            painter.drawPixmap(0, 0, self.width(), self.height(), self.background_pixmap)
            # Add subtle dark scrim overlay
            painter.fillRect(self.rect(), QColor(10, 15, 29, 160))
        else:
            # High-contrast solid dark privacy background
            painter.fillRect(self.rect(), QColor(10, 15, 29, 250))

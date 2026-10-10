"""
Main Application Window for AI Privacy Viewer.

Coordinates sidebar navigation, stacked views, background camera processing,
real-time 3-tier identity telemetry, and Windows-wide screen privacy shield.
"""

from datetime import datetime
from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.ai.camera import CameraWorker
from app.privacy.engine import PrivacyEngine
from app.privacy.overlay import ScreenPrivacyOverlay
from app.ui.styles import DARK_THEME_QSS
from app.ui.views.activity_log_view import ActivityLogView
from app.ui.views.dashboard_view import DashboardView
from app.ui.views.face_registration_view import FaceRegistrationView
from app.ui.views.settings_view import SettingsView
from app.utils.config import config
from app.utils.logger import setup_logger

logger = setup_logger("MainWindow")


class MainWindow(QMainWindow):
    """
    Main PySide6 Application Window.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{config.app_name} - v{config.version}")
        self.setMinimumSize(1100, 720)
        self.resize(1280, 800)

        # Apply dark theme
        self.setStyleSheet(DARK_THEME_QSS)

        # Background Camera worker thread instance
        self.camera_worker = None
        
        # Privacy Engine & Desktop Screen Overlay
        self.privacy_engine = PrivacyEngine(self)
        self.screen_overlay = ScreenPrivacyOverlay()
        self.privacy_shield_simulated = False

        self.init_ui()
        self.setup_clock()
        self.setup_privacy_engine()

    def init_ui(self):
        central_widget = QWidget()
        central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(central_widget)

        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Sidebar Navigation (Left)
        sidebar = self._create_sidebar()
        root_layout.addWidget(sidebar)

        # 2. Main Content Area (Right)
        main_content = QWidget()
        main_content.setObjectName("ContentArea")
        content_layout = QVBoxLayout(main_content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Header
        header = self._create_header()
        content_layout.addWidget(header)

        # Stacked Pages
        self.stacked_widget = QStackedWidget()
        
        self.view_dashboard = DashboardView()
        self.view_registration = FaceRegistrationView()
        self.view_logs = ActivityLogView()
        self.view_settings = SettingsView()

        self.stacked_widget.addWidget(self.view_dashboard)
        self.stacked_widget.addWidget(self.view_registration)
        self.stacked_widget.addWidget(self.view_logs)
        self.stacked_widget.addWidget(self.view_settings)

        content_layout.addWidget(self.stacked_widget, stretch=1)
        root_layout.addWidget(main_content, stretch=1)

        # Connect Dashboard Signals
        self.view_dashboard.start_camera_requested.connect(self.start_camera)
        self.view_dashboard.stop_camera_requested.connect(self.stop_camera)
        self.view_dashboard.toggle_privacy_shield_requested.connect(self.toggle_privacy_shield_test)

        # Connect Registration Signal
        self.view_registration.face_registered.connect(self.on_face_registered)

    def setup_privacy_engine(self):
        """Wire Privacy Engine signals to Desktop Overlay and Dashboard UI."""
        self.privacy_engine.shield_activate_requested.connect(self.on_shield_activate_requested)
        self.privacy_engine.shield_deactivate_requested.connect(self.on_shield_deactivate_requested)
        self.privacy_engine.state_changed.connect(self.on_privacy_state_changed)
        self.privacy_engine.log_emitted.connect(self.view_logs.add_log)
        
        # Connect safe manual dismissal from overlay back to privacy engine
        self.screen_overlay.shield_dismissed.connect(self.privacy_engine.handle_manual_dismiss)

    def on_shield_activate_requested(self, reason: str):
        """Activate full-screen desktop privacy shield and dashboard preview shield."""
        if config.privacy.enable_overlay:
            self.screen_overlay.activate_shield(reason)
        self.view_dashboard.video_preview.set_privacy_shield(True, reason)

    def on_shield_deactivate_requested(self):
        """Deactivate full-screen desktop privacy shield and dashboard preview shield."""
        self.screen_overlay.deactivate_shield()
        self.view_dashboard.video_preview.set_privacy_shield(False)

    def on_privacy_state_changed(self, state: str, reason: str, badge_type: str):
        """Update dashboard privacy badge."""
        self.view_dashboard.badge_privacy.set_status(f"{state}: {reason}", badge_type)

    def on_face_registered(self, name: str, file_path: str):
        self.view_logs.add_log("INFO", "FaceRegistration", f"New user '{name}' registered successfully.")
        if self.camera_worker is not None and self.camera_worker.face_recognizer is not None:
            self.camera_worker.face_recognizer.reload_authorized_users()

    def _create_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("SidebarWidget")
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 20, 16, 20)
        layout.setSpacing(8)

        # App Branding
        app_title = QLabel("AI PRIVACY VIEWER")
        app_title.setObjectName("SidebarTitleLabel")
        app_sub = QLabel("INTELLIGENT SCREEN SHIELD")
        app_sub.setObjectName("SidebarSubtitleLabel")

        layout.addWidget(app_title)
        layout.addWidget(app_sub)
        layout.addSpacing(24)

        # Navigation Buttons
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        self.btn_nav_dashboard = self._create_nav_button("📊  Dashboard", 0, checked=True)
        self.btn_nav_enroll = self._create_nav_button("👤  Face Registration", 1)
        self.btn_nav_logs = self._create_nav_button("📜  Activity Logs", 2)
        self.btn_nav_settings = self._create_nav_button("⚙️  Settings", 3)

        layout.addWidget(self.btn_nav_dashboard)
        layout.addWidget(self.btn_nav_enroll)
        layout.addWidget(self.btn_nav_logs)
        layout.addWidget(self.btn_nav_settings)

        layout.addStretch()

        # Sidebar Footer
        footer_card = QFrame()
        footer_card.setStyleSheet("background-color: #111827; border: 1px solid #1f2937; border-radius: 8px; padding: 10px;")
        footer_layout = QVBoxLayout(footer_card)
        footer_layout.setSpacing(4)
        
        lbl_mode = QLabel("🔒 LOCAL PRIVACY MODE")
        lbl_mode.setStyleSheet("font-size: 11px; font-weight: 700; color: #10b981;")
        lbl_ver = QLabel(f"Version {config.version}")
        lbl_ver.setStyleSheet("font-size: 10px; color: #64748b;")
        
        footer_layout.addWidget(lbl_mode)
        footer_layout.addWidget(lbl_ver)
        layout.addWidget(footer_card)

        return sidebar

    def _create_nav_button(self, text: str, page_index: int, checked: bool = False) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName("NavButton")
        btn.setCheckable(True)
        btn.setChecked(checked)
        btn.clicked.connect(lambda: self.switch_page(page_index, text))
        self.nav_group.addButton(btn)
        return btn

    def _create_header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("HeaderWidget")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(24, 12, 24, 12)

        self.header_title = QLabel("Dashboard")
        self.header_title.setObjectName("HeaderTitle")
        layout.addWidget(self.header_title)

        layout.addStretch()

        # Clock & Status
        self.clock_label = QLabel()
        self.clock_label.setStyleSheet("color: #94a3b8; font-size: 12px; margin-right: 12px;")
        layout.addWidget(self.clock_label)

        self.system_status_pill = QLabel("● System Ready")
        self.system_status_pill.setObjectName("SystemStatusPill")
        self.system_status_pill.setStyleSheet("color: #10b981; border-color: #065f46; background-color: #064e3b;")
        layout.addWidget(self.system_status_pill)

        return header

    def switch_page(self, index: int, title: str):
        self.stacked_widget.setCurrentIndex(index)
        clean_title = title.split(" ", 1)[-1]
        self.header_title.setText(clean_title)

    def setup_clock(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_time)
        self.timer.start(1000)
        self._update_time()

    def _update_time(self):
        now_str = datetime.now().strftime("%a, %b %d • %H:%M:%S")
        self.clock_label.setText(now_str)

    # --- Camera Controls ---
    def start_camera(self):
        if self.camera_worker is not None and self.camera_worker.isRunning():
            return

        self.view_logs.add_log("INFO", "Camera", f"Initializing webcam stream (Index {config.camera.camera_index})...")
        self.camera_worker = CameraWorker(camera_index=config.camera.camera_index)
        
        # Connect signals
        self.camera_worker.frame_ready.connect(self.on_frame_ready)
        self.camera_worker.fps_updated.connect(self.view_dashboard.update_fps)
        self.camera_worker.latency_updated.connect(self.view_dashboard.update_latency)
        self.camera_worker.faces_detected.connect(self.on_faces_detected)
        self.camera_worker.identity_updated.connect(self.on_identity_updated)
        self.camera_worker.gaze_updated.connect(self.on_gaze_updated)
        self.camera_worker.telemetry_updated.connect(self.privacy_engine.process_telemetry)
        self.camera_worker.status_changed.connect(self.on_camera_status_changed)
        self.camera_worker.error_occurred.connect(self.on_camera_error)
        
        self.camera_worker.start()
        self.view_dashboard.set_camera_running(True)
        self.privacy_engine.reset()

    def stop_camera(self):
        if self.camera_worker is not None:
            self.view_logs.add_log("INFO", "Camera", "Stopping webcam stream...")
            self.camera_worker.stop()
            self.camera_worker = None
        self.screen_overlay.deactivate_shield()
        self.view_dashboard.set_camera_running(False)
        self.privacy_engine.reset()

    def on_frame_ready(self, q_image):
        pixmap = QPixmap.fromImage(q_image)
        self.view_dashboard.video_preview.update_frame(pixmap)

    def on_faces_detected(self, count: int):
        self.view_dashboard.card_faces.set_value(str(count))
        if count == 0:
            self.view_dashboard.badge_detection.set_status("NO FACES", "neutral")
        elif count == 1:
            self.view_dashboard.badge_detection.set_status("1 FACE DETECTED", "success")
        else:
            self.view_dashboard.badge_detection.set_status(f"{count} FACES (CROWD)", "warning")

    def on_identity_updated(self, status: str, name: str, conf: float):
        if status == "AUTHORIZED":
            self.view_dashboard.card_identity.set_value(name, f"Authorized ({int(conf * 100)}%)")
            self.view_dashboard.badge_recognition.set_status(f"AUTHORIZED: {name}", "success")
        elif status == "UNCERTAIN":
            self.view_dashboard.card_identity.set_value("UNCERTAIN", f"Suspicious Match ({int(conf * 100)}%)")
            self.view_dashboard.badge_recognition.set_status("UNCERTAIN VIEWER", "warning")
        elif status == "UNKNOWN":
            self.view_dashboard.card_identity.set_value("UNKNOWN", "Unauthorized Viewer")
            self.view_dashboard.badge_recognition.set_status("UNKNOWN VIEWER", "danger")
        elif status == "NO_REGISTERED_USERS":
            self.view_dashboard.card_identity.set_value("Unenrolled", "No face profiles saved")
            self.view_dashboard.badge_recognition.set_status("NO REGISTERED USERS", "warning")
        else:
            self.view_dashboard.card_identity.set_value("None", "No face in view")
            self.view_dashboard.badge_recognition.set_status("STANDBY (DeepFace)", "info")

    def on_gaze_updated(self, direction: str, yaw: float, conf: float):
        self.view_dashboard.card_gaze.set_value(direction, f"Yaw: {yaw:+.1f}° ({int(conf * 100)}%)")
        if direction == "CENTER":
            self.view_dashboard.badge_gaze.set_status("ATTENTIVE (CENTER)", "success")
        elif direction in ("LEFT", "RIGHT"):
            self.view_dashboard.badge_gaze.set_status(f"LOOKING {direction}", "info")
        elif direction == "AWAY":
            self.view_dashboard.badge_gaze.set_status("LOOKING AWAY", "warning")
        else:
            self.view_dashboard.badge_gaze.set_status("STANDBY (MediaPipe)", "neutral")

    def on_camera_status_changed(self, active: bool, msg: str):
        level = "INFO" if active else "WARNING"
        self.view_logs.add_log(level, "Camera", msg)
        if not active:
            self.view_dashboard.set_camera_running(False)

    def on_camera_error(self, err_msg: str):
        self.view_logs.add_log("ERROR", "Camera", err_msg)
        QMessageBox.warning(self, "Camera Error", err_msg)
        self.stop_camera()

    def toggle_privacy_shield_test(self):
        """Toggle privacy shield test mode."""
        self.privacy_shield_simulated = not self.privacy_shield_simulated
        if self.privacy_shield_simulated:
            self.on_shield_activate_requested("Manual Privacy Shield Demonstration")
            self.view_logs.add_log("WARNING", "PrivacyEngine", "Shield activated: Manual test trigger.")
        else:
            self.on_shield_deactivate_requested()
            self.privacy_engine.reset()
            self.view_logs.add_log("INFO", "PrivacyEngine", "Shield deactivated: Manual test ended.")

    def closeEvent(self, event):
        """Cleanly shutdown camera thread and overlay window on exit."""
        if self.screen_overlay is not None:
            self.screen_overlay.close()
        self.stop_camera()
        event.accept()


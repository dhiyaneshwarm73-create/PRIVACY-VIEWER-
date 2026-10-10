"""
Smoke Test for AI Privacy Viewer Desktop UI.

Verifies that all views and widgets instantiate correctly.
"""

import sys
import os
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def test_ui_instantiation():
    # Run in offscreen / minimal mode for headless test environments
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    
    from PySide6.QtWidgets import QApplication
    from app.ui.main_window import MainWindow
    from app.ui.views.dashboard_view import DashboardView
    from app.ui.views.face_registration_view import FaceRegistrationView
    from app.ui.views.activity_log_view import ActivityLogView
    from app.ui.views.settings_view import SettingsView

    app = QApplication.instance() or QApplication(sys.argv)
    
    # Test Main Window creation
    window = MainWindow()
    assert window is not None, "MainWindow failed to instantiate"
    assert window.stacked_widget.count() == 4, "Expected 4 views in stacked widget"

    # Test individual view creation
    dash = DashboardView()
    assert dash.card_fps is not None, "DashboardView card_fps is None"

    reg = FaceRegistrationView()
    assert reg.table is not None, "FaceRegistrationView table is None"

    logs = ActivityLogView()
    assert logs.table.rowCount() >= 1, "ActivityLogView should have initial log row"

    settings = SettingsView()
    assert settings.spin_cam_idx.value() >= 0, "SettingsView spin_cam_idx is invalid"


if __name__ == "__main__":
    test_ui_instantiation()
    print("All UI smoke tests passed successfully!")

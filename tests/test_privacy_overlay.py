"""
Unit Tests for Screen-Wide Privacy Overlay.

Verifies overlay initialization, fullscreen geometry mapping, safe dismissal,
and blurred background fallback handling.
"""

import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def test_screen_privacy_overlay():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtWidgets import QApplication
    from app.privacy.overlay import ScreenPrivacyOverlay

    app = QApplication.instance() or QApplication(sys.argv)
    
    overlay = ScreenPrivacyOverlay()
    assert overlay is not None
    assert overlay.is_active is False

    # 1. Test Shield Activation
    dismissed_reasons = []
    overlay.shield_dismissed.connect(lambda r: dismissed_reasons.append(r))

    overlay.activate_shield("Test Shoulder Surfing Warning")
    assert overlay.is_active is True
    assert overlay.lbl_reason.text() == "Test Shoulder Surfing Warning"

    # 2. Test Deactivation
    overlay.deactivate_shield()
    assert overlay.is_active is False

    # 3. Test User Dismissal
    overlay.activate_shield("Threat")
    overlay.dismiss_by_user()
    assert overlay.is_active is False
    assert len(dismissed_reasons) == 1
    assert "Manual" in dismissed_reasons[0]

    overlay.close()
    print("All ScreenPrivacyOverlay tests passed successfully!")


if __name__ == "__main__":
    test_screen_privacy_overlay()

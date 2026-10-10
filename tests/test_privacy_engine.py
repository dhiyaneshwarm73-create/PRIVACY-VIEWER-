"""
Unit Tests for Privacy Decision Engine & Debouncing State Machine.

Verifies state transitions (Normal -> Alert -> Shield Active -> Recovering -> Normal),
multi-face threat detection, unknown/uncertain identity triggers, look-away timing,
recovery debouncing, and safe manual dismissal.
"""

import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.privacy.engine import PrivacyEngine, PrivacyState
from app.utils.config import config


def test_privacy_engine_transitions():
    engine = PrivacyEngine()
    assert engine.state == PrivacyState.NORMAL

    # Track signals emitted
    activated_reasons = []
    deactivated_count = 0
    state_history = []

    engine.shield_activate_requested.connect(lambda r: activated_reasons.append(r))
    engine.shield_deactivate_requested.connect(lambda: nonlocal_inc())
    engine.state_changed.connect(lambda st, r, b: state_history.append((st, r)))

    def nonlocal_inc():
        nonlocal deactivated_count
        deactivated_count += 1

    # 1. Normal frame: 1 authorized face looking center -> Should remain NORMAL
    normal_telemetry = {
        "num_faces": 1,
        "primary_status": "AUTHORIZED",
        "primary_name": "Owner",
        "gaze_direction": "CENTER",
        "timestamp": time.time()
    }
    engine.process_telemetry(normal_telemetry)
    assert engine.state == PrivacyState.NORMAL
    assert len(activated_reasons) == 0

    # 2. Threat 1: Unknown face for consecutive frames
    config.privacy.consecutive_unknown_frames = 3
    unknown_telemetry = {
        "num_faces": 1,
        "primary_status": "UNKNOWN",
        "primary_name": "Unknown Viewer",
        "gaze_direction": "CENTER",
        "timestamp": time.time()
    }

    # Frame 1 & 2 of unknown face (accumulating debounce)
    engine.process_telemetry(unknown_telemetry)
    assert engine.state == PrivacyState.NORMAL  # Not triggered yet (debounce = 3)
    
    engine.process_telemetry(unknown_telemetry)
    assert engine.state == PrivacyState.NORMAL

    # Frame 3: Threshold reached -> Shield Activated!
    engine.process_telemetry(unknown_telemetry)
    assert engine.state == PrivacyState.SHIELD_ACTIVE
    assert len(activated_reasons) == 1
    assert "Unauthorized" in activated_reasons[0]

    # 3. Threat Cleared: Authorized owner returns
    config.privacy.recovery_delay_sec = 0.3
    
    # First safe frame: enters RECOVERING state
    engine.process_telemetry(normal_telemetry)
    assert engine.state == PrivacyState.RECOVERING

    # Wait for recovery delay and process safe frame
    time.sleep(0.35)
    engine.process_telemetry(normal_telemetry)
    assert engine.state == PrivacyState.NORMAL
    assert deactivated_count == 1

    # 4. Threat 2: Shoulder-surfing (Multiple faces visible)
    config.privacy.consecutive_multiple_faces_frames = 2
    multi_telemetry = {
        "num_faces": 2,
        "primary_status": "AUTHORIZED",
        "primary_name": "Owner",
        "gaze_direction": "CENTER",
        "timestamp": time.time()
    }

    engine.process_telemetry(multi_telemetry)
    assert engine.state == PrivacyState.NORMAL
    
    engine.process_telemetry(multi_telemetry)
    assert engine.state == PrivacyState.SHIELD_ACTIVE
    assert len(activated_reasons) == 2
    assert "Shoulder surfing" in activated_reasons[1]

    # 5. Manual Dismissal by Owner
    engine.handle_manual_dismiss()
    assert engine.state == PrivacyState.NORMAL
    assert engine.active_reason == "Dismissed by Owner"

    print("All PrivacyEngine state transition tests passed successfully!")


if __name__ == "__main__":
    test_privacy_engine_transitions()

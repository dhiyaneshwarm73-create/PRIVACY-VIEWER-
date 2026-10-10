"""
Privacy Decision Engine & Debouncing State Machine.

Analyzes real-time vision telemetry (face count, 3-tier identity, gaze orientation),
evaluates security threat policies, and triggers desktop privacy shield activation
with configurable activation and recovery delays to eliminate screen flickering.
"""

import time
from enum import Enum
from typing import Any, Dict, Optional
from PySide6.QtCore import QObject, Signal

from app.utils.config import config
from app.utils.logger import setup_logger

logger = setup_logger("PrivacyEngine")


class PrivacyState(str, Enum):
    NORMAL = "NORMAL"              # Screen safe, authorized user attentive
    ALERT = "ALERT"                # Potential threat detected, accumulating debounce frames
    SHIELD_ACTIVE = "SHIELD_ACTIVE"# Privacy overlay is active over desktop
    RECOVERING = "RECOVERING"      # Threat cleared, waiting for stability before dismissing shield


class PrivacyEngine(QObject):
    """
    State machine and policy evaluator for intelligent real-time privacy protection.
    """
    # Signals
    state_changed = Signal(str, str, str)       # (state_name, reason, badge_type: 'success'|'warning'|'danger')
    shield_activate_requested = Signal(str)     # (reason)
    shield_deactivate_requested = Signal()
    log_emitted = Signal(str, str, str)         # (level, category, message)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.state: PrivacyState = PrivacyState.NORMAL
        self.active_reason: str = "System Ready"
        
        # Debounce counters
        self.unknown_face_count: int = 0
        self.multiple_faces_count: int = 0
        self.safe_frame_count: int = 0
        
        # Timestamps
        self.look_away_start: Optional[float] = None
        self.recovery_start: Optional[float] = None
        self.manual_dismiss_cooldown_until: float = 0.0
        
        self._last_state_emit_time = 0.0

    def reset(self):
        """Reset all state counters."""
        self.state = PrivacyState.NORMAL
        self.active_reason = "System Normal"
        self.unknown_face_count = 0
        self.multiple_faces_count = 0
        self.safe_frame_count = 0
        self.look_away_start = None
        self.recovery_start = None
        self.state_changed.emit(PrivacyState.NORMAL.value, "Normal (Safe)", "success")

    def process_telemetry(self, telemetry: Dict[str, Any]):
        """
        Evaluate real-time telemetry from camera pipeline.
        
        Args:
            telemetry: Dictionary with keys:
                - num_faces: int
                - primary_status: 'AUTHORIZED' | 'UNCERTAIN' | 'UNKNOWN' | 'NO_REGISTERED_USERS' | 'NO_FACES'
                - primary_name: str
                - gaze_direction: 'CENTER' | 'LEFT' | 'RIGHT' | 'AWAY' | 'UNKNOWN'
                - timestamp: float
        """
        now = time.time()
        
        # If in manual dismiss cooldown, avoid immediate re-triggering for 2 seconds
        if now < self.manual_dismiss_cooldown_until:
            return

        num_faces = telemetry.get("num_faces", 0)
        status = telemetry.get("primary_status", "NO_FACES")
        gaze_dir = telemetry.get("gaze_direction", "CENTER")

        threat_detected = False
        threat_reason = ""

        # Threat Condition 1: Multiple Faces Detected (Shoulder Surfing)
        if num_faces > 1:
            self.multiple_faces_count += 1
            if self.multiple_faces_count >= config.privacy.consecutive_multiple_faces_frames:
                threat_detected = True
                threat_reason = f"Shoulder surfing detected: {num_faces} people in view"
        else:
            self.multiple_faces_count = max(0, self.multiple_faces_count - 1)

        # Threat Condition 2: Unknown or Uncertain Face Detected
        if not threat_detected and num_faces >= 1:
            if status == "UNKNOWN":
                self.unknown_face_count += 1
                if self.unknown_face_count >= config.privacy.consecutive_unknown_frames:
                    threat_detected = True
                    threat_reason = "Unauthorized unknown viewer detected"
            elif status == "UNCERTAIN":
                self.unknown_face_count += 1
                if self.unknown_face_count >= (config.privacy.consecutive_unknown_frames + 1):
                    threat_detected = True
                    threat_reason = "Uncertain identity viewer detected near screen"
            else:
                self.unknown_face_count = max(0, self.unknown_face_count - 1)

        # Threat Condition 3: Authorized User Looking Away (If Enabled)
        if not threat_detected and config.privacy.enable_look_away:
            if num_faces == 1 and status == "AUTHORIZED" and gaze_dir == "AWAY":
                if self.look_away_start is None:
                    self.look_away_start = now
                elif (now - self.look_away_start) >= config.privacy.look_away_delay_sec:
                    threat_detected = True
                    threat_reason = f"Look-away protection ({config.privacy.look_away_delay_sec:.0f}s)"
            else:
                self.look_away_start = None

        # --- State Machine Transitions ---

        if threat_detected:
            self.recovery_start = None
            self.safe_frame_count = 0
            
            if self.state != PrivacyState.SHIELD_ACTIVE:
                self.state = PrivacyState.SHIELD_ACTIVE
                self.active_reason = threat_reason
                logger.warning(f"Privacy threat confirmed: {threat_reason}")
                self.log_emitted.emit("WARNING", "PrivacyEngine", f"Shield Activated: {threat_reason}")
                self.state_changed.emit(self.state.value, threat_reason, "danger")
                self.shield_activate_requested.emit(threat_reason)

        else:
            # Threat cleared or normal condition
            if self.state == PrivacyState.SHIELD_ACTIVE or self.state == PrivacyState.RECOVERING:
                # Begin recovery debounce timer
                if self.recovery_start is None:
                    self.recovery_start = now
                    self.state = PrivacyState.RECOVERING
                    self.state_changed.emit(self.state.value, "Stabilizing...", "warning")
                elif (now - self.recovery_start) >= config.privacy.recovery_delay_sec:
                    # Successfully recovered
                    self.state = PrivacyState.NORMAL
                    self.active_reason = "Normal (Safe)"
                    self.recovery_start = None
                    self.unknown_face_count = 0
                    self.multiple_faces_count = 0
                    logger.info("Threat cleared. Deactivating Privacy Shield.")
                    self.log_emitted.emit("INFO", "PrivacyEngine", "Shield Deactivated: Return to normal state.")
                    self.state_changed.emit(self.state.value, "Normal (Safe)", "success")
                    self.shield_deactivate_requested.emit()
            else:
                if self.state != PrivacyState.NORMAL:
                    self.state = PrivacyState.NORMAL
                    self.active_reason = "Normal (Safe)"
                    self.state_changed.emit(self.state.value, "Normal (Safe)", "success")

    def handle_manual_dismiss(self):
        """User dismissed the shield manually."""
        self.state = PrivacyState.NORMAL
        self.active_reason = "Dismissed by Owner"
        self.unknown_face_count = 0
        self.multiple_faces_count = 0
        self.recovery_start = None
        self.manual_dismiss_cooldown_until = time.time() + 2.5
        self.state_changed.emit(self.state.value, "Dismissed (Manual)", "success")
        self.log_emitted.emit("INFO", "PrivacyEngine", "Shield dismissed manually by owner.")

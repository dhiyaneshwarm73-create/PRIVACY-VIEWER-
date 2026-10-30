"""
Comprehensive Test Runner for AI Privacy Viewer.

Discovers and executes all unit, integration, and UI smoke test suites,
reporting detailed execution metrics and pass/fail statuses.
"""

import sys
import time
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

TEST_SCRIPTS = [
    ("Face Detection (YOLOv8 & Cascade Fallback)", "tests/test_face_detection.py"),
    ("Face Recognition (3-Tier & Embeddings)", "tests/test_face_recognition.py"),
    ("Gaze & Head Pose Tracking (PnP / MediaPipe)", "tests/test_gaze_tracking.py"),
    ("Performance Profiler & Frame Decoupling", "tests/test_performance_pipeline.py"),
    ("Privacy Decision Engine (Debouncing State Machine)", "tests/test_privacy_engine.py"),
    ("Desktop Screen Privacy Overlay (Safe Dismissal)", "tests/test_privacy_overlay.py"),
    ("PySide6 Desktop UI & Navigation Smoke Tests", "tests/test_ui_smoke.py"),
]


def run_all():
    print("=" * 70)
    print("        AI PRIVACY VIEWER - AUTOMATED TEST SUITE")
    print("=" * 70)

    total = len(TEST_SCRIPTS)
    passed = 0
    failed = 0
    start_time = time.time()

    for idx, (name, script_path) in enumerate(TEST_SCRIPTS, 1):
        print(f"\n[{idx}/{total}] Running: {name} ...")
        t0 = time.time()
        res = subprocess.run(
            [sys.executable, script_path],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True
        )
        elapsed = time.time() - t0

        if res.returncode == 0:
            passed += 1
            print(f"  --> PASSED ({elapsed:.2f}s)")
        else:
            failed += 1
            print(f"  --> FAILED ({elapsed:.2f}s) (Exit Code {res.returncode})")
            if res.stdout:
                print(f"  [STDOUT]:\n{res.stdout.strip()}")
            if res.stderr:
                print(f"  [STDERR]:\n{res.stderr.strip()}")

    total_time = time.time() - start_time
    print("\n" + "=" * 70)
    print(f"TEST EXECUTION SUMMARY: {passed}/{total} Passed | {failed} Failed | Time: {total_time:.2f}s")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)

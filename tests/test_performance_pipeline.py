"""
Unit Tests for Performance Monitoring, FPS Profiling, and Bounded Queue Decoupling.
"""

import queue
import sys
import time
from pathlib import Path
import numpy as np

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.utils.performance import FPSTracker, LatencyTimer, PipelineProfiler


def test_fps_tracker():
    tracker = FPSTracker(buffer_size=10)
    assert tracker.fps == 0.0

    # Simulate 5 frames at 30 FPS (interval ~33ms)
    for _ in range(5):
        time.sleep(0.033)
        fps = tracker.tick()

    assert fps > 15.0 and fps < 45.0, f"Expected FPS near 30, got {fps}"
    assert tracker.frame_time_ms > 0.0

    tracker.reset()
    assert tracker.fps == 0.0


def test_latency_timer_and_profiler():
    profiler = PipelineProfiler(history_size=10)

    # 1. LatencyTimer context manager
    with LatencyTimer("test_block") as timer:
        time.sleep(0.02)  # 20ms

    assert timer.elapsed_ms >= 15.0
    profiler.record("detection", timer.elapsed_ms)

    # Record multiple entries
    profiler.record("detection", 18.0)
    profiler.record("recognition", 45.0)
    profiler.record("gaze", 12.0)

    avg_det = profiler.get_average_ms("detection")
    assert avg_det > 10.0

    summary = profiler.get_summary()
    assert "detection" in summary
    assert "recognition" in summary
    assert summary["recognition"] == 45.0


def test_bounded_frame_queue_behavior():
    """
    Verify that a bounded queue (maxsize=1) discards older frames and only retains the newest frame.
    """
    q = queue.Queue(maxsize=1)

    frame_1 = np.ones((10, 10, 3), dtype=np.uint8) * 1
    frame_2 = np.ones((10, 10, 3), dtype=np.uint8) * 2
    frame_3 = np.ones((10, 10, 3), dtype=np.uint8) * 3

    # Producer simulates rapid camera acquisition
    for frame in [frame_1, frame_2, frame_3]:
        try:
            q.get_nowait()
        except queue.Empty:
            pass
        try:
            q.put_nowait(frame)
        except queue.Full:
            pass

    # Consumer reads newest frame
    latest = q.get_nowait()
    assert np.array_equal(latest, frame_3), "Bounded queue should retain only the newest frame"
    assert q.empty(), "Queue should now be empty"

    print("All Performance and Pipeline tests passed successfully!")


if __name__ == "__main__":
    test_fps_tracker()
    test_latency_timer_and_profiler()
    test_bounded_frame_queue_behavior()

"""
Performance Tracking and FPS Monitoring Utility.

Provides low-overhead FPS calculation and latency measurement for real-time CV pipelines.
"""

import time
from collections import deque
from typing import Optional


class FPSTracker:
    """
    Measures frames per second (FPS) over a rolling window.
    """
    def __init__(self, buffer_size: int = 30):
        self.buffer_size = buffer_size
        self.timestamps = deque(maxlen=buffer_size)
        self.fps: float = 0.0
        self.last_frame_time: Optional[float] = None
        self.frame_time_ms: float = 0.0

    def tick(self) -> float:
        """
        Record a new frame arrival and compute current rolling FPS.
        
        Returns:
            Current estimated FPS
        """
        now = time.perf_counter()
        
        if self.last_frame_time is not None:
            self.frame_time_ms = (now - self.last_frame_time) * 1000.0

        self.last_frame_time = now
        self.timestamps.append(now)

        if len(self.timestamps) > 1:
            elapsed = self.timestamps[-1] - self.timestamps[0]
            if elapsed > 0:
                self.fps = (len(self.timestamps) - 1) / elapsed

        return self.fps


class LatencyTimer:
    """
    Context manager to profile execution time of specific AI pipeline blocks.
    """
    def __init__(self, label: str = "Block"):
        self.label = label
        self.start_time: float = 0.0
        self.elapsed_ms: float = 0.0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.elapsed_ms = (time.perf_counter() - self.start_time) * 1000.0

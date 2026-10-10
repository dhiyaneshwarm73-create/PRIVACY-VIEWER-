"""
Performance Tracking and FPS Monitoring Utility.

Provides low-overhead FPS calculation, latency measurement, and thread-safe frame buffers
for real-time CV pipelines.
"""

import time
from collections import deque
from typing import Dict, Optional


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

        return round(self.fps, 1)

    def reset(self):
        self.timestamps.clear()
        self.fps = 0.0
        self.last_frame_time = None
        self.frame_time_ms = 0.0


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


class PipelineProfiler:
    """
    Rolling latency profiler for complete AI pipeline stages (Capture, Detection, Recognition, Gaze, Render).
    """
    def __init__(self, history_size: int = 20):
        self.history_size = history_size
        self._latencies: Dict[str, deque] = {
            "detection": deque(maxlen=history_size),
            "recognition": deque(maxlen=history_size),
            "gaze": deque(maxlen=history_size),
            "total_inference": deque(maxlen=history_size),
        }

    def record(self, stage: str, elapsed_ms: float):
        if stage not in self._latencies:
            self._latencies[stage] = deque(maxlen=self.history_size)
        self._latencies[stage].append(elapsed_ms)

    def get_average_ms(self, stage: str) -> float:
        d = self._latencies.get(stage)
        if d and len(d) > 0:
            return round(sum(d) / len(d), 1)
        return 0.0

    def get_summary(self) -> Dict[str, float]:
        return {k: self.get_average_ms(k) for k in self._latencies}


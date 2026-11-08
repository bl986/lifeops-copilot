import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    """Sliding-window limiter kept in memory (resets on restart; fine for one small instance)."""

    def __init__(self, max_calls: int, window_seconds: float):
        self.max_calls = max_calls
        self.window = window_seconds
        self._hits = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, now: float | None = None) -> int:
        """Record a hit and return 0 if allowed, otherwise the seconds to wait."""
        now = time.monotonic() if now is None else now
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] >= self.window:
                hits.popleft()
            if len(hits) >= self.max_calls:
                return max(1, int(self.window - (now - hits[0])) + 1)
            hits.append(now)
            self._prune(now)
            return 0

    def _prune(self, now: float) -> None:
        if len(self._hits) > 5000:
            stale = [k for k, v in self._hits.items() if not v or now - v[-1] >= self.window]
            for k in stale:
                del self._hits[k]
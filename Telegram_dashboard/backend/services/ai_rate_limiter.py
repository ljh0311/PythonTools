import time
from collections import deque

from backend.config import AI_RATE_LIMIT_PER_MINUTE


class RateLimitExceeded(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(
            f"AI rate limit reached ({AI_RATE_LIMIT_PER_MINUTE}/min). "
            f"Try again in {retry_after}s."
        )


class AIRateLimiter:
    def __init__(self, max_per_minute: int = AI_RATE_LIMIT_PER_MINUTE):
        self.max_per_minute = max(1, max_per_minute)
        self._timestamps: deque[float] = deque()

    def check(self) -> None:
        now = time.time()
        window_start = now - 60
        while self._timestamps and self._timestamps[0] < window_start:
            self._timestamps.popleft()

        if len(self._timestamps) >= self.max_per_minute:
            retry_after = max(1, int(60 - (now - self._timestamps[0])) + 1)
            raise RateLimitExceeded(retry_after)

        self._timestamps.append(now)

    def status(self) -> dict[str, int]:
        now = time.time()
        window_start = now - 60
        while self._timestamps and self._timestamps[0] < window_start:
            self._timestamps.popleft()
        used = len(self._timestamps)
        return {
            "limit_per_minute": self.max_per_minute,
            "used_last_minute": used,
            "remaining": max(0, self.max_per_minute - used),
        }


ai_rate_limiter = AIRateLimiter()

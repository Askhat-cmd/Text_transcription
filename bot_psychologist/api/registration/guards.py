"""Runtime guards for registration flows."""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from typing import Deque, DefaultDict


class LinkAttemptGuard:
    """In-memory sliding-window guard for telegram link attempts."""

    def __init__(self, *, max_attempts: int = 5, window_seconds: int = 900) -> None:
        self._max_attempts = max_attempts
        self._window_seconds = window_seconds
        self._failed_attempts: DefaultDict[str, Deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    def _cleanup(self, telegram_user_id: str, now_ts: float) -> None:
        queue = self._failed_attempts[telegram_user_id]
        cutoff = now_ts - self._window_seconds
        while queue and queue[0] < cutoff:
            queue.popleft()
        if not queue:
            self._failed_attempts.pop(telegram_user_id, None)

    async def is_blocked(self, telegram_user_id: str) -> bool:
        now_ts = time.time()
        async with self._lock:
            self._cleanup(telegram_user_id, now_ts)
            queue = self._failed_attempts.get(telegram_user_id)
            return bool(queue and len(queue) >= self._max_attempts)

    async def check_and_record(self, telegram_user_id: str, *, success: bool) -> bool:
        """Record attempt and return True when user is currently blocked."""
        now_ts = time.time()
        async with self._lock:
            if success:
                self._failed_attempts.pop(telegram_user_id, None)
                return False

            self._cleanup(telegram_user_id, now_ts)
            queue = self._failed_attempts[telegram_user_id]
            queue.append(now_ts)
            self._cleanup(telegram_user_id, now_ts)
            return len(self._failed_attempts.get(telegram_user_id, ())) >= self._max_attempts


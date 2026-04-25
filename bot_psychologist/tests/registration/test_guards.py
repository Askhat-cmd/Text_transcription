from __future__ import annotations

import asyncio

import pytest

from api.registration.guards import LinkAttemptGuard


@pytest.mark.asyncio
async def test_guard_not_blocked_initially() -> None:
    guard = LinkAttemptGuard(max_attempts=5, window_seconds=900)
    assert await guard.is_blocked("tg1") is False


@pytest.mark.asyncio
async def test_guard_blocked_after_5_failures() -> None:
    guard = LinkAttemptGuard(max_attempts=5, window_seconds=900)
    for _ in range(5):
        await guard.check_and_record("tg1", success=False)
    assert await guard.is_blocked("tg1") is True


@pytest.mark.asyncio
async def test_guard_clears_on_success() -> None:
    guard = LinkAttemptGuard(max_attempts=5, window_seconds=900)
    for _ in range(4):
        await guard.check_and_record("tg1", success=False)
    assert await guard.is_blocked("tg1") is False
    await guard.check_and_record("tg1", success=True)
    assert await guard.is_blocked("tg1") is False

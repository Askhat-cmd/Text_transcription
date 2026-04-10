from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api import routes


def test_stats_user_counter_bounded() -> None:
    original_seen = routes._seen_users.copy()
    original_count = routes._stats["total_users_approx"]
    try:
        routes._seen_users = set(f"user_{i}" for i in range(routes._STATS_USER_LIMIT))
        routes._stats["total_users_approx"] = routes._STATS_USER_LIMIT

        routes._record_user("brand_new_user")

        assert len(routes._seen_users) == 1
        assert routes._stats["total_users_approx"] == routes._STATS_USER_LIMIT + 1
    finally:
        routes._seen_users = original_seen
        routes._stats["total_users_approx"] = original_count


def test_stats_user_counter_no_duplicate() -> None:
    original_seen = routes._seen_users.copy()
    original_count = routes._stats["total_users_approx"]
    try:
        routes._seen_users = set()
        routes._stats["total_users_approx"] = 0

        routes._record_user("same_user")
        routes._record_user("same_user")
        routes._record_user("same_user")

        assert routes._stats["total_users_approx"] == 1
    finally:
        routes._seen_users = original_seen
        routes._stats["total_users_approx"] = original_count

from __future__ import annotations

from api.admin_routes import admin_router, admin_router_v1

from tests.contract.admin_route_snapshot_support import (
    compare_snapshots,
    execute_route_case,
    route_cases,
)


def _inventory_keys() -> set[str]:
    keys: set[str] = set()
    for router in (admin_router, admin_router_v1):
        for route in router.routes:
            for method in sorted(m for m in route.methods if m not in {"HEAD", "OPTIONS"}):
                keys.add(f"{method} {route.path}")
    return keys


def _case_keys() -> set[str]:
    return {f"{case.method} {case.route_pattern}" for case in route_cases()}


def test_snapshot_cases_cover_all_registered_admin_routes() -> None:
    assert _case_keys() == _inventory_keys()


def test_snapshot_case_count_matches_registered_admin_routes() -> None:
    assert len(route_cases()) == len(_inventory_keys())


def test_snapshot_before_after_self_compare_is_clean() -> None:
    before = {"routers": {}, "responses": []}
    after = {"routers": {}, "responses": []}
    assert compare_snapshots(before, after) == []


for _case in route_cases():
    def _make_test(case):
        def _test() -> None:
            result = execute_route_case(case)
            assert result["status_code"] == case.expected_status

        _test.__name__ = f"test_route_snapshot_{case.case_id}"
        return _test

    globals()[f"test_route_snapshot_{_case.case_id}"] = _make_test(_case)

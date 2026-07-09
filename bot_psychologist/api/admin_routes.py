"""Thin admin router aggregator for the decomposed admin surface.

The public contract stays unchanged: main.py imports admin_router and
admin_router_v1 from this module. Route registration order is preserved by the
module import sequence below.
"""

from __future__ import annotations

from .admin_surface_bootstrap import admin_router, admin_router_v1, data_loader
from . import admin_runtime_compat as _admin_runtime_compat  # noqa: F401
from . import admin_surface_helpers as _admin_surface_helpers  # noqa: F401
from . import admin_runtime_effective_payload as _admin_runtime_effective_payload  # noqa: F401
from . import admin_diagnostics_payload as _admin_diagnostics_payload  # noqa: F401
from . import admin_config_schema as _admin_config_schema  # noqa: F401
from . import admin_config_routes as _admin_config_routes  # noqa: F401
from . import admin_prompt_routes as _admin_prompt_routes  # noqa: F401
from . import admin_agent_ops_routes as _admin_agent_ops_routes  # noqa: F401
from . import admin_misc_routes as _admin_misc_routes  # noqa: F401

__all__ = ["admin_router", "admin_router_v1", "data_loader"]

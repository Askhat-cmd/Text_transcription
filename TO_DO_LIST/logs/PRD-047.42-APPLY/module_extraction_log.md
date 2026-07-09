# PRD-047.42-APPLY module extraction log

- `91-173` -> `bot_psychologist/api/admin_runtime_compat.py` (`92547a9`)
- `178-233` -> `bot_psychologist/api/admin_surface_bootstrap.py` (`c50c075`)
- `235-665` -> `bot_psychologist/api/admin_surface_helpers.py` (`4e45680`)
- `668-956` -> `bot_psychologist/api/admin_runtime_effective_payload.py` (`4b3ef29`)
- `959-982` -> `bot_psychologist/api/admin_diagnostics_payload.py` (`98d112f`)
- `985-1132` -> `bot_psychologist/api/admin_config_schema.py` (`0ed30f5`)
- `1148-1432` -> `bot_psychologist/api/admin_config_routes.py` (`bac1a9b`)
- `1447-1705` -> `bot_psychologist/api/admin_prompt_routes.py` (`bcca654`)
- `1716-1905` -> `bot_psychologist/api/admin_agent_ops_routes.py` (`644d500`)
- `1916-2144` -> `bot_psychologist/api/admin_misc_routes.py` (`e5e5c1a`)

Route-order preservation:
- `bot_psychologist/api/admin_routes.py` is reduced to a thin aggregator that imports `admin_surface_bootstrap` first and then imports the route-bearing modules in the original boundary-map order.
- The side-effect import sequence is the route-registration sequence. This preserves the original FastAPI matcher order for overlapping admin paths such as schema/static routes vs parameterized config routes.

Legacy-compat handling:
- `admin_runtime_compat.py`
- `admin_runtime_effective_payload.py`
- `admin_config_routes.py`
- `admin_agent_ops_routes.py`

These fragments were moved as-is per the accepted map. No cleanup/removal happened inside this PRD.

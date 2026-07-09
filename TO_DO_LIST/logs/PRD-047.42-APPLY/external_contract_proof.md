# PRD-047.42-APPLY external contract proof

Verified public import contract:

```text
bot_psychologist/api/main.py:244
from .admin_routes import admin_router, admin_router_v1  # Admin Config Panel (legacy + v1)
```

Proof:
- `api/main.py` was not edited by this PRD.
- `bot_psychologist/api/admin_routes.py` still exports `admin_router` and `admin_router_v1`.
- The thin aggregator also re-exports `data_loader` to preserve the historical import surface.
- Route registration order is preserved by module import order inside the aggregator.

Result:
- external import contract unchanged
- `main.py` code changes required: `0`

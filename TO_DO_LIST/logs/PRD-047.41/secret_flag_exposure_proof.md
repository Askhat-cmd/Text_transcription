# PRD-047.41 Secret Flag Exposure Proof

- covered payloads: `/api/admin/runtime/effective` live payload plus contract tests
- contract tests: `tests/contract/test_effective_config_registry_v1041.py`
- requirement: secret entries expose only `{"is_set": bool}` as `current_value`.

| Flag | Status | current_value | Source |
| --- | --- | --- | --- |
| ADMIN_ACCESS_KEY | secret | {"is_set": false} | env |
| ADMIN_INVITE_KEY | secret | {"is_set": false} | env |
| ADMIN_USERNAME | secret | {"is_set": false} | env |
| DEV_API_KEY | secret | {"is_set": false} | env |
| INTERNAL_TELEGRAM_KEY | secret | {"is_set": false} | env |
| OPENAI_API_KEY | secret | {"is_set": true} | env |
| TELEGRAM_BOT_TOKEN | secret | {"is_set": false} | env |
| TELEGRAM_WEBHOOK_SECRET | secret | {"is_set": false} | env |
| TEST_API_KEY | secret | {"is_set": false} | env |
| VOYAGE_API_KEY | secret | {"is_set": true} | env |

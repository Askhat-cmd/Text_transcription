# API Contracts

## `GET /api/status`
Оперативный health/status payload API runtime.

## `GET /api/registry` и `GET /api/registry/`
Список sources + статистика реестра.

## `GET /api/dashboard` и `GET /api/dashboard/`
Сводный runtime payload `botdb_dashboard_summary_v1`:
- `sources`
- `blocks`
- `chroma`
- `governance`
- `enrichment`
- `recent_sources`
- `warnings`

## `POST /api/query/`
Семантический retrieval endpoint.

Compatibility note:
- `sd_level` принимается для backward compatibility.
- `sd_level` игнорируется как retrieval filter (deprecated legacy signal).

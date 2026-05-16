# Legacy SD

## Что это
SD (Spiral Dynamics) - исторический semantic слой ранних версий проекта.

## Текущий статус
- deprecated
- disabled by default
- не участвует в retrieval/runtime authority
- не участвует в readiness score

## Где может встречаться
- historical blocks metadata (`sd_level`)
- registry historical aggregates (`sd_distribution`)
- compatibility API schema/query contracts

## Legacy-only Explicit Mode
Разрешено включать только для debug/legacy сценариев при двух флагах одновременно:
- `enabled=true`
- `explicit_legacy_mode=true`

Без explicit режима SD labeler не должен вызываться.

## Config Finalization (HF1)
- `sd_labeling.enabled=false` и `legacy_sd_labeling.enabled=false` в canonical `config.yaml`.
- Env overrides допустимы только как runtime input и не должны перезаписывать файл `config.yaml`.

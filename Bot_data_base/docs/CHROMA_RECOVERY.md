# Chroma Recovery

## Diagnostic Sequence
1. Проверить dashboard `chroma.count`.
2. Проверить direct Chroma count (`collection.count()`).
3. Сверить с expected focus blocks (`247`).

## Strict Gate
Гейт проходит только при согласованности:
- registry focus blocks
- dashboard blocks
- dashboard chroma count
- direct chroma count

## Controlled Reindex
Если direct Chroma count не совпадает:
- сделать backup manifest
- reindex только focus source
- повторить live smoke + reconciliation

## Safety
- Не мутировать `all_blocks_merged.json` и `registry.json` в recovery-only цикле.
- Не включать historical proof как override для live mismatch.

# Source Hygiene

## Production Target State
- active sources: `1`
- focus source: `123__кузница_духа`
- non-focus production blocks: `0`

## Policy
- Focus source защищён от удаления.
- Zero-block/test-like sources могут удаляться controlled route.
- Перед delete создаётся registry snapshot.

## Operational Expectations
- registry остаётся focus-only для production runtime.
- Dashboard и Chroma должны быть согласованы по source set.

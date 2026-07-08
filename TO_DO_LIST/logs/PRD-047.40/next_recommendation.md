# PRD-047.40 Next Recommendation

- Keep `user_level_adapter` runtime compat references untouched in this PRD; current verdict is `active` because accepted-but-ignored compatibility surfaces still exist in active runtime/API code.
- Clean remaining user-level compatibility shims only in a dedicated follow-up PRD that also updates API/debug metadata contracts together.
- `bot_psychologist/docs/testing.md` still documents removed Phase 1/2/3 legacy scripts and should be refreshed in a documentation-only follow-up.

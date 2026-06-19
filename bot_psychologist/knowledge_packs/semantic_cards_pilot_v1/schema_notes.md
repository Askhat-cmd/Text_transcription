# Semantic Card Schema Notes

- `writer_can_ignore` must always be `true`.
- `quote_policy` must be explicit.
- Practice cards require `practice_policy=practice_allowed_if_explicit`.
- Cards must not contain raw long source text or hidden evaluator notes.
- Cards are converted into `writer_kb_payload_v1` candidates and remain advisory.

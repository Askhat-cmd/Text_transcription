You are generating offline enrichment JSON for one governed knowledge chunk.

Return ONLY valid JSON object. No markdown.

Safety and format:
- summary_candidate must be paraphrased (120..500 chars, Russian UTF-8).
- Never output long direct quotes from source text.
- Never start summary with source opening phrasing.
- Do not mutate governance authority fields.

Lens allowlist (exact values only):
shame, guilt, anger, grief, fear_of_rejection, self_criticism, avoidance, procrastination,
perfectionism, achievement, boundaries, relationships, attachment, loneliness, body_awareness,
hyperarousal, hypoarousal, low_resource, burnout, control, inner_parts, identity, meaning,
values, rumination, anxiety, freeze, safety, practice_integration.

Review reasons enum (exact values only):
low_confidence, insufficient_context, mixed_intent_unclear, split_merge_unclear,
lens_mapping_uncertain, practice_context_unclear, safety_context_unclear, summary_quality_uncertain.

Low-resource avoid_when rule (mandatory for safety-critical chunks):
If safety_flags_original contains `practice_requires_low_resource_check`,
`avoid_when` MUST include at least one canonical phrase:
- "при низком ресурсе, истощении или острой нестабильности"
- "когда у пользователя мало сил, кризис или выраженная перегрузка"

Good example:
{"avoid_when":["при низком ресурсе, истощении или острой нестабильности","когда нужна срочная кризисная поддержка вместо исследования"]}

Bad example:
{"avoid_when":["если практика не подходит"]}

Output schema:
{
  "summary_candidate": "string 120..500",
  "lens_family_candidates": ["allowlist enums"],
  "tags": ["string"],
  "use_when": ["string"],
  "avoid_when": ["string"],
  "self_contained_score": 0.0,
  "self_contained_reason": "string",
  "split_merge_suggestion": {"action": "keep|split|merge_with_previous|merge_with_next|manual_review", "reason": "string"},
  "confidence": 0.0,
  "needs_human_review": false,
  "review_reasons": ["enum values only"]
}

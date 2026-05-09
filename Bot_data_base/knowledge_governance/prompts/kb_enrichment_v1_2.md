You are generating offline enrichment JSON for one governed knowledge chunk.

Return ONLY one valid JSON object.
No markdown. No comments.

Hard constraints:
- Do not output long direct quotes from source text.
- Do not start `summary_candidate` with source opening phrases.
- Do not output user-facing therapist advice.
- Do not mutate governance authority (`chunk_type_original`, `allowed_use_original`, `safety_flags_original`).

`summary_candidate` rules:
- Length: 120..500 chars.
- Russian UTF-8 text.
- Paraphrased retrieval/context-assembly value only.

Controlled enum for `lens_family_candidates`:
- shame
- guilt
- anger
- grief
- fear_of_rejection
- self_criticism
- avoidance
- procrastination
- perfectionism
- achievement
- boundaries
- relationships
- attachment
- loneliness
- body_awareness
- hyperarousal
- hypoarousal
- low_resource
- burnout
- control
- inner_parts
- identity
- meaning
- values
- rumination
- anxiety
- freeze
- safety
- practice_integration

Rules for `lens_family_candidates`:
- Must contain only exact strings from the allowlist above.
- Do not translate enum values.
- Do not invent new lens names.
- If unsure, return fewer candidates and set `needs_human_review=true`.

Controlled enum for `review_reasons`:
- low_confidence
- insufficient_context
- mixed_intent_unclear
- split_merge_unclear
- lens_mapping_uncertain
- practice_context_unclear
- safety_context_unclear
- summary_quality_uncertain

Rules for `review_reasons`:
- Use only enum values above.
- Do not output free-form long Russian sentences in this field.
- If no review reason is needed, return empty array.

Good example (lens):
"lens_family_candidates": ["self_criticism", "achievement", "shame"]

Bad example (lens):
"lens_family_candidates": ["самокритика", "страх оценки", "внутренняя программа"]
Reason: values are not from allowlist.

Good example (review_reasons):
"review_reasons": ["lens_mapping_uncertain"]

Bad example (review_reasons):
"review_reasons": ["Нужна дополнительная проверка интерпретации контекста и точности."]
Reason: free-form text breaks machine aggregation.

Required output schema:
{
  "summary_candidate": "string 120..500",
  "lens_family_candidates": ["allowlist enum values"],
  "tags": ["string"],
  "use_when": ["string"],
  "avoid_when": ["string"],
  "self_contained_score": 0.0,
  "self_contained_reason": "string",
  "split_merge_suggestion": {
    "action": "keep|split|merge_with_previous|merge_with_next|manual_review",
    "reason": "string"
  },
  "confidence": 0.0,
  "needs_human_review": false,
  "review_reasons": ["controlled enum values"]
}

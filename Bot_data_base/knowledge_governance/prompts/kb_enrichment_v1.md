Ты работаешь в режиме offline-enrichment для внутренней базы знаний.

Задача:
сформировать JSON-кандидат enrichment для одного governed chunk.

Критически важно:
- Верни ТОЛЬКО JSON-объект, без markdown и комментариев.
- Не цитируй длинно исходный текст.
- Не пиши "книга говорит", "автор говорит", "согласно Кузнице".
- Не создавай user-facing советы бота.
- Не меняй governance authority (`chunk_type`, `allowed_use`, `safety_flags`).

Обязательные поля ответа:
{
  "summary_candidate": "строка 120-500 символов",
  "lens_family_candidates": ["строка"],
  "tags": ["строка"],
  "use_when": ["строка"],
  "avoid_when": ["строка"],
  "self_contained_score": 0.0,
  "self_contained_reason": "строка",
  "split_merge_suggestion": {
    "action": "keep|split|merge_with_previous|merge_with_next|manual_review",
    "reason": "строка"
  },
  "confidence": 0.0,
  "needs_human_review": false,
  "review_reasons": ["строка"]
}

Правила качества:
- summary_candidate: полезная смысловая переформулировка для retrieval, не цитата.
- lens_family_candidates: 3-8 значений, если уверенности нет — меньше и `needs_human_review=true`.
- tags: до 12 коротких тегов.
- use_when / avoid_when: по 1-4 коротких пункта.
- Если есть `practice_requires_low_resource_check` в safety_flags, в avoid_when явно отметь low-resource/кризис.

Формат:
- ТОЛЬКО валидный JSON.
- UTF-8 русский текст.

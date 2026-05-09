Ты работаешь в режиме offline-enrichment для внутренней базы знаний.

Задача:
сформировать JSON-кандидат enrichment для одного governed chunk.

Критически важно:
- Верни ТОЛЬКО JSON-объект, без markdown и комментариев.
- Не цитируй длинно исходный текст.
- Не начинай summary_candidate фразой из начала исходного текста.
- Не повторяй дословно предложения из исходного текста.
- Не используй длинные авторские формулировки как есть.
- Не пиши "книга говорит", "автор говорит", "согласно Кузнице", "в данном тексте".
- Не создавай user-facing советы бота.
- Не меняй governance authority (`chunk_type`, `allowed_use`, `safety_flags`).

Требования к summary_candidate:
- 120-500 символов.
- Русский UTF-8.
- Это сжатая смысловая переформулировка о том, зачем chunk нужен retrieval/context assembly.
- Без прямых цитат и без ссылок на книгу/автора.

Плохой пример:
{
  "summary_candidate": "Три причины, по которым программа «несовершенное Я» держится так крепко..."
}

Почему плохо: начало summary копирует исходный chunk.

Хороший пример:
{
  "summary_candidate": "Фрагмент помогает распознать, как самокритика закрепляется через эмоционально значимый опыт и автоматизацию реакции, чтобы в диалоге точнее отразить паттерн и выбрать безопасный следующий шаг без давления."
}

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
- lens_family_candidates: 3-8 значений при уверенном совпадении, иначе меньше и `needs_human_review=true`.
- tags: до 12 коротких тегов.
- use_when / avoid_when: по 1-4 коротких пункта.
- Если есть `practice_requires_low_resource_check` в safety_flags, в avoid_when явно отметь low-resource/кризис.

Формат:
- ТОЛЬКО валидный JSON.

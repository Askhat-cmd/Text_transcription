# PRD_TASKS — Упрощение и оптимизация системы ретривала Bot Psychologist

## Этап 0 — Подготовка и аудит
- [x] 0.1 Создать PRD_TASKS.md с полным чек‑листом
- [x] 0.2 Создать ветку `refactor/simplify-retrieval-pipeline`
- [x] 0.3 Сделать checkpoint‑коммит
- [x] 0.4 Запустить тесты baseline: `cd tests && python -m pytest -v --tb=short > tests_before.txt`
- [x] 0.5 Сохранить `tests_before.txt` как baseline
- [x] 0.6 Найти все упоминания `stage_filter|sd_filter|complexity_cap` (`grep -r ...`)
- [x] 0.7 Зафиксировать список затронутых файлов в этом PRD_TASKS

Затронутые файлы (stage/sd/complexity):
- `bot_psychologist/bot_agent/answer_adaptive.py`
- `bot_psychologist/bot_agent/answer_basic.py`
- `bot_psychologist/bot_agent/answer_graph_powered.py`
- `bot_psychologist/bot_agent/answer_sag_aware.py`
- `bot_psychologist/bot_agent/chroma_loader.py`
- `bot_psychologist/bot_agent/decision/decision_gate.py`
- `bot_psychologist/bot_agent/retrieval/__init__.py`
- `bot_psychologist/bot_agent/retrieval/stage_filter.py`
- `bot_psychologist/api/models.py`
- `bot_psychologist/api/routes.py`
- `bot_psychologist/logging_config.py`
- `bot_psychologist/tests/test_db_api_client.py`
- `bot_psychologist/tests/test_decision_gate.py`
- `bot_psychologist/tests/test_decision_table.py`
- `bot_psychologist/tests/test_sd_filter.py`
- `bot_psychologist/tests/test_stage_filter.py`

## Этап 1 — Удаление Stage‑фильтра
- [x] 1.1 Удалить файл `bot_agent/retrieval/stage_filter.py`
- [x] 1.2 Найти все импорты `stage_filter|StageFilter|complexity_cap`
- [x] 1.3 Удалить импорты `stage_filter` из найденных файлов
- [x] 1.4 В `answer_adaptive.py` удалить блок вызова stage_filter (после rerank)
- [x] 1.5 Убедиться: pipeline = initial → SD → rerank → cap → LLM
- [x] 1.6 Найти log‑строки `STAGE_FILTER|complexity_cap|stage_filter`
- [x] 1.7 Удалить найденные log‑строки
- [x] 1.8 Найти UI‑компоненты `stage|complexity` (frontend/static)
- [x] 1.9 Удалить элементы Stage‑фильтра из трасс‑панели (Pipeline Timeline)
- [x] 1.10 Удалить из Config Snapshot параметры stage
- [x] 1.11 Проверить в трейсе: нет строк "Stage фильтр: skip/active"
- [x] 1.12 Прогнать: `python -m pytest tests/ -k "retrieval or filter" -v`
- [x] 1.13 Тестовый запрос через API `/api/v1/questions/adaptive-stream`
- [x] 1.14 В логах нет `STAGE_FILTER`, пайплайн доходит до LLM
- [x] 1.15 Коммит: `feat: remove stage_filter module and all references`

## Этап 2 — Рефакторинг SD‑фильтра
- [x] 2.1 Найти `sd_filter.py` в `bot_agent/retrieval/`
- [x] 2.2 Удалить `sd_filter.py` (или очистить как deprecated)
- [x] 2.3 В `answer_adaptive.py` найти блок `[SD_FILTER]/after_sd_filter`
- [x] 2.4 Удалить вызов `sd_filter` (initial → rerank напрямую)
- [x] 2.5 Удалить импорт `sd_filter`
- [x] 2.6 Удалить log‑строки `SD_FILTER`, `After SD filter`, `SD_COMPAT`
- [x] 2.7 `sd_classifier.py` оставить без изменений
- [x] 2.8 Найти место формирования контекста LLM
- [x] 2.9 Убедиться что `sd_level` и `user_state` передаются в prompt_builder/llm_answerer
- [x] 2.10 Добавить в system_prompt секцию с `sd_level` и `user_state`
- [x] 2.11 Проверить в трейсе: `sd_level` присутствует в System Prompt
- [x] 2.12 В трасс‑панели убрать строку "SD фильтр: skip/active"
- [x] 2.13 Оставить отображение SD‑уровня пользователя (SD: BLUE · 0.85)
- [x] 2.14 В Config Snapshot убрать `SD_CONFIDENCE_THRESHOLD` если он только для фильтра
- [x] 2.15 `python -m pytest tests/ -k "sd or classifier" -v`
- [x] 2.16 Тест: блоки с любым SD доходят до LLM
- [x] 2.17 В трейсе нет "After SD filter", SD‑уровень виден в промпте
- [x] 2.18 Коммит: `feat: remove sd_filter, pass sd_level to LLM prompt`

## Этап 3 — Упрощение Confidence Scorer
- [ ] 3.1 Открыть `confidence_scorer.py`
- [ ] 3.2 Убрать `voyage_confidence` из формулы
- [ ] 3.3 Формула: local_similarity + delta_top1_top2 + state_match + question_clarity
- [ ] 3.4 FAST_PATH порог `low=0.40` остаётся
- [ ] 3.5 Упростить confidence cap до фиксированного TOP‑K
- [ ] 3.6 Удалить log‑строки `CONFIDENCE_CAP` с разбивкой уровней
- [ ] 3.7 Оставить строку `[CONFIDENCE] score=X level=Y → FAST_PATH: yes/no`
- [ ] 3.8 Убедиться есть `RETRIEVAL_TOP_K` в config/.env (текущее = 3)
- [ ] 3.9 Поменять `RETRIEVAL_TOP_K` на 5
- [ ] 3.10 В `answer_adaptive.py`: финальный срез `blocks[:config.RETRIEVAL_TOP_K]`
- [ ] 3.11 В админке поле TOP‑K = 5
- [ ] 3.12 `python -m pytest tests/ -k "confidence" -v`
- [ ] 3.13 Тест: "To LLM" = 5 блоков
- [ ] 3.14 Тест приветствия: FAST_PATH работает
- [ ] 3.15 Коммит: `feat: simplify confidence scorer, fixed TOP-K=5`

## Этап 4 — Оптимизация Voyage Reranker
- [ ] 4.1 Открыть `voyage_reranker.py`
- [ ] 4.2 TOP‑K после rerank = 5
- [ ] 4.3 При fallback оставить исходный порядок TF‑IDF, не менять количество
- [ ] 4.4 Убрать лог "reranked top_k=2..." при ошибке, заменить на `[VOYAGE] fallback...`
- [ ] 4.5 В конфиге `VOYAGE_TOP_K = 5`
- [ ] 4.6 В админке "Voyage TOP‑K" = 5
- [ ] 4.7 Интеграционный тест Voyage (python -c ... test_connection)
- [ ] 4.8 Тест‑запрос: лог `[VOYAGE] rerank success, top_k=5`
- [ ] 4.9 Коммит: `fix: voyage reranker top_k=5, fix fallback logging`

## Этап 5 — Обновление тестов
- [ ] 5.1 Запустить все тесты: `python -m pytest tests/ -v --tb=short > tests_after.txt`
- [ ] 5.2 Сравнить baseline: `diff tests_before.txt tests_after.txt`
- [ ] 5.3 Удалить/переписать тесты Stage‑фильтра
- [ ] 5.4 Удалить/переписать тесты SD‑фильтра
- [ ] 5.5 Обновить тесты confidence_scorer под новую формулу
- [ ] 5.6 Написать `test_retrieval_pipeline_simplified.py` (4 сценария из PRD)
- [ ] 5.7 Написать `test_confidence_scorer_simple.py`
- [ ] 5.8 Финальный прогон: `python -m pytest tests/ -v`
- [ ] 5.9 Все тесты зелёные или xfail с пояснением
- [ ] 5.10 Коммит: `test: update tests for simplified retrieval pipeline`

## Этап 6 — Финальная проверка и документация
- [ ] 6.1 Запустить `Bot_data_base` на `8003`
- [ ] 6.2 Запустить бота на `8000`
- [ ] 6.3 Отправить 3 тестовых сообщения через UI
- [ ] 6.4 В трейсе нет Stage/SD фильтров, есть Rerank и LLM
- [ ] 6.5 Обновить `README.md` (убрать упоминание Stage/SD фильтров)
- [ ] 6.6 Добавить в README раздел "Архитектура ретривала"
- [ ] 6.7 Обновить `CHANGELOG.md` (v0.6.0)
- [ ] 6.8 `git add -A`
- [ ] 6.9 Коммит: `refactor: simplified retrieval pipeline v0.6.0 — remove stage/sd filters`
- [ ] 6.10 Создать PR `refactor/simplify-retrieval-pipeline → main`
- [ ] 6.11 В PR описать: что удалено/упрощено + ссылка на PRD_TASKS

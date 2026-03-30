# PRD_TASKS_modernization_bot_psychologist

Источник: `PRD Модернизация и усиление бота-психолога.md`  
Проект: `bot_psychologist`  
Статус: в работе

## Правила выполнения

- Работать фазами по порядку: `0 -> 1 -> 2 -> 3 -> 4 -> 5`.
- После каждой фазы запускать проверки и фиксировать метрики.
- Не нарушать hard constraints из PRD.
- В коммитах указывать фазу в сообщении (`[Phase X.Y] ...`).

## Фаза 0 — Backup + Baseline

- [x] 0.1 Просмотреть текущие точки интеграции в `bot_agent/`, `config/`, `tests/`.
- [x] 0.2 Добавить `bot_psychologist/scripts/chroma_backup.py`.
- [x] 0.3 Создать backup ChromaDB с тегом `pre-e5-migration`.
- [x] 0.4 Добавить `bot_psychologist/scripts/bootstrap_eval_sets.py`.
- [x] 0.5 Создать `bot_psychologist/tests/eval/` и файлы:
  - [x] `classifier_eval_set.json`
  - [x] `routing_eval_set.json`
  - [x] `retrieval_eval_set.json`
  - [x] `baseline.json`
- [x] 0.6 Заполнить `baseline.json` числами после первого прогона eval.
- [x] 0.7 Gate: baseline зафиксирован, можно переходить к фазе 1.

## Фаза 1 — Embedding Migration (E5)

- [x] 1.1 Добавить `bot_psychologist/bot_agent/embedding_provider.py` (интерфейс + E5 provider).
- [x] 1.2 Подключить provider в retrieval pipeline.
- [x] 1.3 Обновить `chroma_loader.py` для безопасного rebuild (`--confirm`, новая коллекция).
- [x] 1.4 Подготовить параллельную коллекцию `psychologist_e5*` без удаления старой.
- [x] 1.5 Добавить/запустить eval retrieval compare.
- [x] 1.6 Gate: `Recall@5` и `MRR` не хуже baseline.

## Фаза 2 — Conditional Reranker

- [x] 2.1 Добавить `bot_psychologist/bot_agent/reranker_gate.py`.
- [x] 2.2 Подключить gate в retrieval pipeline.
- [x] 2.3 Проверить ограничение вызовов reranker (`<= 25%` на eval-наборе).
- [x] 2.4 Gate: тесты reranker зеленые.

## Фаза 3 — Level-0 Fast Detector

- [x] 3.1 Добавить `bot_psychologist/bot_agent/fast_detector.py`.
- [x] 3.2 Подключить в `state_classifier.py` перед Level-1.
- [x] 3.3 Подключить в `sd_classifier.py` перед Level-1.
- [x] 3.4 Gate: classifier-тесты зеленые.

## Фаза 4 — Feature Flags

- [x] 4.1 Добавить `bot_psychologist/config/feature_flags.py`.
- [x] 4.2 Подключить флаги к новым компонентам фаз 1–3.
- [x] 4.3 Обновить `bot_psychologist/.env.example`.
- [x] 4.4 Gate: каждый флаг переключается независимо.

## Фаза 5 — Улучшения интеллекта

- [x] 5.1 Адаптивная длина ответа (`response_formatter.py`).
- [x] 5.2 VALIDATION-first в маршрутизации (`decision_table.py`, `signal_detector.py`).
- [ ] 5.3 Детектор противоречий (`contradiction_detector.py`).
- [ ] 5.4 Cross-session summary memory (`conversation_memory.py` расширение).
- [ ] 5.5 Progressive RAG (`progressive_rag.py`, веса блоков в SQLite).

## Лог выполнения

- [x] Создан файл задач и начат запуск PRD.
- [x] Реализованы скрипты `chroma_backup.py` и `bootstrap_eval_sets.py`.
- [x] Сформированы eval-наборы в `bot_psychologist/tests/eval/`.
- [x] Создан backup: `backups/chroma_pre-e5-migration_20260330_122309`.
- [x] Закрыта Фаза 0 (baseline + backup).
- [x] Начата Фаза 1: добавлен `embedding_provider.py`, semantic memory переведена на provider-слой.
- [x] Фаза 1.2: retriever получил semantic fallback через `EmbeddingProvider` (API -> semantic -> TF-IDF).
- [x] Фаза 1.3/1.4: добавлен безопасный rebuild в `chroma_loader.py` + CLI `scripts/rebuild_chroma_index.py`.
- [x] Добавлены тесты `test_retriever_fallback.py` (semantic fallback) и `test_chroma_loader_rebuild.py` (safety guards).
- [x] Фаза 1.5/1.6: `scripts/eval_retrieval.py --compare` выполнен при активном Bot_data_base: `recall@5=1.0`, `mrr=1.0`, gate=PASS.
- [x] Фаза 2.1/2.2: добавлен `reranker_gate.py`, интегрирован conditional rerank в `answer_adaptive.py`.
- [x] Фаза 2.4: добавлены тесты `test_reranker_gate.py` и расширен `test_retrieval_pipeline_simplified.py` — зеленые.
- [x] Фаза 2.3: прогнан `scripts/eval_reranker_usage.py --enforce` (100 запросов), доля reranker = 10%.

- [x] Фаза 3.1/3.2/3.3/3.4: добавлен `fast_detector.py`, интегрирован в `state_classifier.py` и `sd_classifier.py`; тесты зелёные.
- [x] Фаза 4.1/4.2/4.3/4.4: добавлен `config/feature_flags.py`, флаги подключены в retriever/state/sd/answer_adaptive, gate по независимому переключению пройден.
- [x] Фаза 5.1: в `response_formatter.py` добавлен `calculate_target_length()` + ограничение ответа по числу предложений.
- [x] Фаза 5.2: добавлено правило `VALIDATION_FIRST_NEW_TOPIC` (rule_id=100) через новые сигналы в `signal_detector.py`.

# Architecture Overview

## High-Level Flow
Рабочий контур построен как последовательность специализированных модулей с явными контрактами данных:
User Message -> State Analyzer -> Thread Manager -> Memory Retrieval -> Context Assembly -> Diagnostic Card -> Writer Move Compliance -> Writer -> Validator / Quality Trace -> Memory Update.

Эта схема отделяет диагностику, сбор контекста, генерацию и пост-валидацию. Главный принцип: Writer не принимает системные архитектурные решения в одиночку.

## State Analyzer
State Analyzer классифицирует текущую фазу пользователя, риск-профиль и требуемую глубину ответа. Он задает routing hints для следующих слоев и не выполняет генерацию финального текста.

## Thread Manager
Thread Manager управляет continuity по треду: активные фреймы, continuity-маркеры, low-resource сигналы и диагностические флаги. Его задача — удерживать состояние беседы согласованным между turn'ами.

## Memory Retrieval
Memory Retrieval извлекает релевантные memory items и governed KB candidates через восстановленный BotDB/Chroma API path. Retrieval не должен отдавать raw full text в user trace и не должен обходить governance policy.

## Context Assembly
Context Assembly формирует управляемый context package: recent dialogue summary, memory snippets, KB lenses, safety flags. Это слой, который ограничивает prompt payload и предотвращает "все-в-один" prompt anti-pattern.

## Diagnostic Card
Diagnostic Card агрегирует признаки состояния, гипотезы, риски и safe-next-focus. Карта служит структурой для Writer и Validator, а не заменяет клиническую диагностику.

## Writer Move Compliance
Слой compliance проверяет, что planned writer move согласован с Diagnostic Card и ограничениями safety/governance. Нарушения фиксируются в trace и могут понижать confidence.

## Writer
Writer формирует пользовательский ответ на основе собранного контекста и compliance constraints. Writer не должен напрямую цитировать governed internal sources и не является источником истинности по safety policy.

## Validator / Quality Trace
Validator проверяет ответ и trace-контракт: структура, консистентность, запрещенные паттерны, redaction-safe diagnostics. Для KB-enrichment отдельный validator контролирует quote-risk, unknown lens, invariant consistency и low-resource guardrails.

## Knowledge Base / RAG
KB использует governed blocks с deterministic metadata (`chunk_type`, `allowed_use`, `safety_flags`, lens family). LLM enrichment добавляет advisory metadata (summary/lens/tags/use_when/avoid_when), но не заменяет governance authority.

## Memory Update
После выдачи ответа система обновляет память и trace-состояние, сохраняя raw turn history и диагностические признаки для следующего цикла.

## Planned: Async Turn LLM Summary
Планируемый слой `PRD-045.6.3` добавит async LLM-summary для turn context с deterministic fallback. Цель — улучшить semantic continuity recent dialogue без блокировки response path.

## Planned: Diagnostic Center
Diagnostic Center v1 отложен. Он должен запускаться только после:
- controlled apply enriched overlay,
- retrieval eval readiness,
- и стабилизации context-quality слоя (async turn summary).

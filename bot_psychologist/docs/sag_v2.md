# Knowledge Package Format

This note describes the structure of knowledge blocks consumed by retrieval.

## Core Block Fields

- `block_id`
- `title`
- `summary`
- `content`
- `keywords`
- `source` metadata (author, link, timestamps when available)

## Retrieval Usage

- Blocks are indexed for semantic and keyword retrieval.
- Selected chunks are passed to prompt assembly.
- Chunk metadata is included in debug trace for observability.

## Validation Guidelines

- Keep `block_id` stable across updates.
- Preserve text quality in `summary` and `content`.
- Keep metadata fields consistent for deterministic rendering in UI trace.

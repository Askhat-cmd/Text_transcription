# PRD-047.22 Future Graduation Notes

        - payload_version: writer_kb_payload_v1
        - payload_source: legacy_selected_hit
        - structured_payload_used: true
        - legacy_semantic_hits_used: false
        - accepted_overlay_used: false
        - chunk_type: concept
        - quote_policy: paraphrase_only
        - truncation_strategy: paragraph_then_sentence_boundary
        - writer_received_structured_payload: true

        ## Temporary Paths Left
        - legacy semantic hit trimming remains as fallback when WRITER_KB_PAYLOAD_ENABLED=false
- legacy semantic hit trimming remains as fallback if payload builder fails
- overlay metadata enrichment plumbing exists but is disabled by default

        ## Planned Retirement Path
        - collect PRD-047.23 live evidence with structured payload enabled in developer-local mode
- retire blind Writer-side semantic hit trimming after stable shadow-to-apply graduation
- consolidate flags during PRD-047.24 unified retrieval runtime work

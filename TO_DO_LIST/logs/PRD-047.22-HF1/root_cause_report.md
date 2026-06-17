# PRD-047.22-HF1 Root Cause Report

- identified_root_cause: The previous PRD-047.22 live smoke used ad-hoc PowerShell-piped inline Python with Cyrillic source text, which corrupted the HTTP query before it reached the backend. That produced a gibberish retrieval query, zero selected writer chunks, and `payload_chunk_count=0`. In addition, the previous smoke did not own or verify the backend lifecycle, so it could also hit a process started without `WRITER_KB_PAYLOAD_ENABLED=true`.

## Evidence
- Live debug trace with broken transport showed `writer_kb_payload_trace.enabled=false` or `payload_chunk_count=0`.
- App logs for the broken smoke recorded the adaptive question and retrieval query as `??? ...` instead of Russian text.
- Live HTTP rerun with an ASCII-only JSON body (`json.dumps(..., ensure_ascii=True).encode('ascii')`) produced `payload_chunk_count=1` and a direct concept answer.
- No retrieval, Chroma, registry, or metadata code path changes were required to recover the payload trace.

- fix_strategy: `minimal_live_path_repair`

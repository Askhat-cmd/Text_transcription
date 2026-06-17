# PRD-047.23 Chunk Boundary Audit

## C23-001 / 5943bece-db10-460a-bc21-7e23e6485925
- cut_class: `stored_preview_used_as_full_content`
- stored_block_found: `True`
- stored_text_char_count: `1883`
- content_excerpt_char_count: `700`
- total_sent_char_count: `700`
- content_truncated: `False`
- truncation_strategy: `none`
- ends_mid_word: `True`
- explanation: Stored block is longer than trace excerpt and source contains the longer form.

## C23-002 / 5943bece-db10-460a-bc21-7e23e6485925
- cut_class: `runtime_payload_sentence_truncation`
- stored_block_found: `True`
- stored_text_char_count: `1883`
- content_excerpt_char_count: `1575`
- total_sent_char_count: `1575`
- content_truncated: `True`
- truncation_strategy: `sentence_boundary`
- ends_mid_word: `False`
- explanation: Runtime trace marks sentence-boundary truncation.

## C23-003 / f68050f9-d789-4d8b-b5b1-d6302ddfb88e
- cut_class: `none`
- stored_block_found: `True`
- stored_text_char_count: `1244`
- content_excerpt_char_count: `1233`
- total_sent_char_count: `1713`
- content_truncated: `False`
- truncation_strategy: `none`
- ends_mid_word: `False`
- explanation: Stored/source boundary still needs manual follow-up.

## C23-003 / cc979440-d02f-4bff-8920-59982597b4cc
- cut_class: `none`
- stored_block_found: `True`
- stored_text_char_count: `482`
- content_excerpt_char_count: `480`
- total_sent_char_count: `1713`
- content_truncated: `False`
- truncation_strategy: `none`
- ends_mid_word: `False`
- explanation: Stored/source boundary still needs manual follow-up.

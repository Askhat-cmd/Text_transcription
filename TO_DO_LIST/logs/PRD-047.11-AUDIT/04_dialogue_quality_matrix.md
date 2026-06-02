# Dialogue Quality Matrix

| case_id | group | status | failed_checks |
| --- | --- | --- | --- |
| AUDIT-GR-001 | greeting_restraint | failed | max_chars, must_not_include_any |
| AUDIT-GR-002 | greeting_repair | failed | max_chars |
| AUDIT-GR-003 | greeting_restraint | failed | bad_phrase, known_bad_phrase_absent, must_include_any, trace_contains_bad_phrase |
| AUDIT-FU-001 | followup_reliability | failed | bad_phrase, known_bad_phrase_absent, must_include_any, trace_contains_bad_phrase |
| AUDIT-FU-002 | followup_reliability | failed | not_repeated_mechanism_x3 |
| AUDIT-FU-003 | followup_reliability | passed | - |
| AUDIT-DA-001 | direct_answer | failed | bad_phrase, known_bad_phrase_absent, min_chars, must_include_any, must_not_include_any, trace_contains_bad_phrase |
| AUDIT-DA-002 | direct_answer | failed | max_chars, must_include_any, not_repeated_mechanism_x3 |
| AUDIT-DA-003 | direct_answer | failed | min_chars, must_include_any |
| AUDIT-RP-001 | repair | passed | - |
| AUDIT-RP-002 | repair | failed | max_chars |
| AUDIT-RP-003 | repair | failed | bad_phrase, known_bad_phrase_absent, must_include_any, must_not_include_any, trace_contains_bad_phrase |
| AUDIT-BOSS-001 | boss_scenario | passed | - |
| AUDIT-BOSS-002 | boss_scenario | failed | bad_phrase, known_bad_phrase_absent, must_include_any, trace_contains_bad_phrase |
| AUDIT-BOSS-003 | boss_scenario | failed | must_include_any, not_repeated_mechanism_x3 |
| AUDIT-OE-001 | over_explaining | failed | bad_phrase, known_bad_phrase_absent, max_chars, must_not_include_any, trace_contains_bad_phrase |
| AUDIT-OE-002 | over_explaining | failed | bad_phrase, known_bad_phrase_absent, max_chars, trace_contains_bad_phrase |
| AUDIT-OE-003 | over_explaining | passed | - |


# User Prompt Equivalence

- PRD: `PRD-047.42-APPLY-12`
- Full snapshot byte identical: `True`
- All `user_prompt` values identical: `True`

| case | prompt_match | before_sha1 | after_sha1 | before_lines | after_lines | first_diff |
| --- | --- | --- | --- | --- | --- | --- |
| mvp_free_overview | True | `d2305057cbbf3a898d637f30c91af3c145b8e53b` | `d2305057cbbf3a898d637f30c91af3c145b8e53b` | 329 | 329 | no difference |
| mvp_free_rich_request | True | `79986d3569d740a75a31c7dec84dff60f2d8909d` | `79986d3569d740a75a31c7dec84dff60f2d8909d` | 329 | 329 | no difference |
| safe_guided_direct | True | `78cc0973cbe5807e0588499bd51556cac6d4eff3` | `78cc0973cbe5807e0588499bd51556cac6d4eff3` | 319 | 319 | no difference |

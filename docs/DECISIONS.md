# Architecture Decisions

## ADR-111 - `WRITER_USER_TEMPLATE.format(...)` stays one render call while argument families move behind explicit typed builders

Status: accepted

Date: 2026-07-13

Delivery: PRD-047.42-APPLY-11 accepted in main commit `0c35d2f`.

Context: after PRD-047.42-APPLY-10, the next largest remaining `_call_llm` responsibility was no longer a sequential helper-like block but the giant `WRITER_USER_TEMPLATE.format(...)` render call itself. That render is one Python call with roughly `170` named arguments, not a series of statements, so trying to “cut the render” the same way as slice1/2/3 would either split the template call itself or force hidden prompt-assembly rewrites. The first low-risk families inside that render were the five argument groups built mostly from direct `ctx.get(..., default)` normalization and one deterministic diagnostic summary formatter.

Decision:
- keep `WRITER_USER_TEMPLATE.format(...)` as one single render call;
- move selected argument families out by extracting the value computation into one helper plus one typed dataclass, not by splitting the render call or rewriting the template text;
- keep each kwarg name in the render call explicit as `slice4_inputs.<field>` rather than using dict unpacking or `locals()` tricks;
- preserve `conversation_context=formatted_context` inline at its original position because it is intentionally outside the extracted families;
- preserve the intentional raw behavior of `writer_move_instruction_summary=ctx.get(...) or "нет"` without adding a new `str()` wrapper;
- require byte-identical before/after proof not only for `llm_response` and full `last_debug`, but also for the exact `user_prompt` text line-by-line, because this is the first PRD that changes where prompt argument values are assembled.

Consequences: the project now has a proven decomposition pattern for the giant render spine without changing the prompt template itself. Future render-slice PRDs should continue by moving coherent argument families behind explicit typed builders while leaving the single render call intact until the render spine becomes small enough that a different decomposition style is justified.

## ADR-110 - First state-coupled `_call_llm` extraction returns a debug patch and applies it once at the call site

Status: accepted

Date: 2026-07-13

Delivery: PRD-047.42-APPLY-10 implementation completed in workspace; delivery metadata pending follow-up commit sync.

Context: PRD-047.42-APPLY-6 mapped `writer_kb_payload_and_trace_capture` as the first pre-provider `_call_llm` cluster that is not pure: it computes prompt input and also writes seven keys into `self.last_debug`. PRD-047.42-APPLY-7 and APPLY-9 had already proven the pure-helper pattern for ctx-only slices, but that pattern cannot be copied verbatim here because the helper must not mutate `self` directly and the project still needs proof that the resulting debug surface is byte-identical.

Decision:
- move the cluster into a dedicated helper module `writer_agent_call_llm_slice3.py`;
- keep the helper pure and return one typed object with exactly two outputs: `writer_kb_payload_text` and `last_debug_patch`;
- keep `writer_kb_payload_fallback_reason` internal to the helper because it is local-only and does not cross the cluster boundary;
- apply the patch in `_call_llm` with one explicit `self.last_debug.update(slice3_inputs.last_debug_patch)` call rather than seven inline assignments;
- preserve the original key order inside the returned patch for review readability;
- require byte-identical before/after snapshot proof on the full `last_debug`, not only on `llm_response`.

Consequences: the decomposition track now has a proven pattern for state-coupled pre-provider `_call_llm` slices without widening helper side effects or exporting unnecessary local variables. Later debug-writing clusters can reuse this boundary style, while larger render/provider/response clusters remain separate decisions.

## ADR-109 - `_call_llm` extraction helpers may export only true cross-cluster values; `local_only` detector workspace stays internal

Status: accepted

Date: 2026-07-10

Delivery: PRD-047.42-APPLY-9 accepted in main commit `0d9e6bb`.

Context: PRD-047.42-APPLY-6 mapped `request_detectors_and_mvp_override_block` as one pre-provider cluster inside `_call_llm`, and PRD-047.42-APPLY-9 then used the accepted map plus a live grep review to confirm that only `5` of the cluster's `14` local names actually flow into the remaining prompt-render path. The other `9` names exist only to compute `rich_user_request` and the final `mvp_override_block`. Exporting all `14` values would technically work, but it would widen the giant-method surface, make future slices noisier, and dilute the point of the dependency map.

Decision:
- keep the second `_call_llm` slice as one explicit helper plus one typed return object;
- export only the `5` names that cross the cluster boundary: `explicit_answer_need`, `sarcasm_or_negative_feedback`, `repair_user_dissatisfaction`, `overruled_constraints`, and `mvp_override_block`;
- keep the `9` detector/intermediate names internal to the helper because the accepted map classifies them as `local_only`;
- preserve the same explicit unpacking rule from ADR-107: no `locals().update()`, no dict-to-namespace tricks, and no helper side effects;
- treat “does this name actually leave the cluster?” as a required review question for every later `_call_llm` slice, especially before the project reaches the stateful `self.last_debug` clusters.

Consequences: later decomposition steps inside `_call_llm` now have a tighter rule than “move code out”: every slice must minimize the exported namespace to only the names that truly survive beyond the cut. That keeps the remaining giant method reviewable and prevents temporary detector/workspace variables from becoming accidental long-lived contracts.

## ADR-108 - Boundary-mapping structural contracts must freeze historical baselines instead of re-parsing live giant-method shape

Status: accepted

Date: 2026-07-10

Delivery: PRD-047.42-APPLY-8 accepted in main commit `e615581`.

Context: PRD-047.42-APPLY-6 added a local-variable inventory over the original `804`-line `_call_llm` shape and PRD-047.42-APPLY-7 then performed the first real extraction inside that method. The accepted behavior stayed stable under the dedicated `_call_llm` snapshot gate, but one APPLY-6 contract test broke anyway because it recalculated inventory from the live post-slice method and compared the result to expectations that belonged to the accepted pre-slice structure. That kind of contract would fail again on every future `_call_llm` slice even when runtime behavior stayed unchanged.

Decision:
- freeze the accepted APPLY-6 variable inventory from commit `e5f5f32` into a dedicated JSON fixture with explicit provenance;
- keep the APPLY-6 runner capable of live analysis, but add an optional `source_text` path so the same analyzer can be used against historical file text without rewriting production logs;
- rewrite only the stale structural test to compare against the frozen baseline fixture rather than recomputing expectations from the current live `_call_llm`;
- preserve byte-identical default behavior of `build_variable_inventory()` when `source_text` is not provided;
- treat boundary-mapping contracts as historical evidence contracts once real decomposition starts, unless a later PRD explicitly remaps and re-freezes them.

Consequences: future `_call_llm` slices can continue without accumulating false red tests from accepted old maps. Live analyzer output remains useful for new reports, while frozen contracts remain tied to the exact accepted structural baseline they are meant to protect.

## ADR-107 - First `_call_llm` code moves must use explicit local-namespace extraction, not helper side effects

Status: accepted

Date: 2026-07-10

Delivery: PRD-047.42-APPLY-7 accepted in main commit `9249f04`.

Context: PRD-047.42-APPLY-6 mapped `_call_llm` into `11` clusters and showed that the first safe code-move target was not provider dispatch but two adjacent ctx-only preparation clusters. Unlike earlier `writer_agent.py` slices, these clusters did not correspond to standalone class or module helpers already present in the file. They were local-variable builders embedded directly inside `_call_llm`, and their outputs were consumed later by the giant `WRITER_USER_TEMPLATE.format(...)` block plus the following detector cluster. A careless extraction approach such as `locals().update(...)`, implicit dict unpacking into the local namespace, or helper side effects would make future review and regression analysis much harder.

Decision:
- extract the first `_call_llm` slice into one explicit module-level helper plus one typed return object;
- keep the extraction pure and ctx-only, with no `self.last_debug` writes and no hidden state mutation;
- return named fields explicitly and unpack them back into the same downstream local variable names inside `_call_llm`;
- do not use `locals().update()`, `globals()`, or any implicit namespace injection trick;
- keep `practice_gate` local inside the helper because the accepted dependency graph classified it as `local_only`;
- leave provider dispatch, response parsing, prompt rendering, and all state-coupled debug-writing clusters for later dedicated slices.

Consequences: `_call_llm` can now be decomposed incrementally without giving up reviewability. Future apply slices should follow the same rule inside giant methods: explicit helper boundaries, explicit return objects, explicit local unpacking, and no namespace magic.

## ADR-106 - _call_llm must be remapped read-only before any further decomposition because its preparation block is a giant sequential state graph, not a named helper set

Status: accepted

Date: 2026-07-10

Delivery: PRD-047.42-APPLY-6 accepted in main commit `e5f5f32`.

Context: after PRD-047.42-APPLY-5, the remaining `writer_agent.py` core was no longer a set of easy lifecycle or fallback edges. The largest active method, `_call_llm`, still spanned `804` lines and mixed ctx default seeding, knowledge/practice/freedom normalization, context-budget shaping, rich-request detectors, writer-kb formatting, prompt rendering, prompt-constraint append, runtime/system-prompt selection, provider dispatch, and result/debug parsing in one flat sequence. Unlike `admin_routes.py`, it did not already decompose into clearly named sub-functions. A blind APPLY PRD here would risk moving the wrong chunk first or underestimating the number of hidden local-variable and `self.last_debug` dependencies.

Decision:
- treat `_call_llm` as a new Stage-2 mapping target before any further apply step;
- keep PRD-047.42-APPLY-6 strictly read-only on production code;
- build an exact internal boundary map for `_call_llm`, not only a rough “before provider / provider / after provider” split;
- inventory local variables by assignment line, dependency names, and downstream scope (`writer_prompt_input`, `provider_dispatch_input`, `local_only`);
- explicitly mark clusters that mutate `self.last_debug`, because those are not pure helper candidates without returning debug patches or moving stateful helpers;
- capture a mocked-provider `_call_llm` snapshot baseline over three realistic scenarios so APPLY-7 has behavior evidence before cutting anything.

Consequences: future `_call_llm` decomposition is now gated by a real map instead of intuition. The next safe apply step should start from the smallest pre-provider extraction edge identified by the map, while provider dispatch and response parsing stay separate until the preparation block is no longer one giant mixed responsibility chain.

## ADR-105 - writer_agent lifecycle spine moves by mixin, preserving the public write-path and legacy temperature monkeypatch seam

Status: accepted

Date: 2026-07-10

Delivery: PRD-047.42-APPLY-5 accepted in main commit `a419ead`.

Context: after slices 1-3, `writer_agent.py` had already shed pure helpers, static fallback helpers, and the first self-bound fallback/state cluster, but the next smallest meaningful slice was no longer a utility edge. The remaining target pair, `_resolve_runtime_settings()` plus the public async `write()` entrypoint, forms the lifecycle spine of the class: it decides runtime temperature/max-tokens, branches through `safety_active`, calls `_call_llm`, falls back on failure/empty output, and routes the final text through answer-compliance repair. Rewriting this pair into free functions or widening the slice to include giant methods would raise behavior risk unnecessarily. A second constraint also appeared: accepted tests still monkeypatch `bot_agent.multiagent.agents.writer_agent.get_temperature_for_agent`, so moving temperature resolution blindly would break a real compatibility seam even though runtime behavior itself would stay the same.

Decision:
- move `_resolve_runtime_settings()` and `write()` together into a dedicated `WriterAgentLifecycleMixin`;
- make `WriterAgent` inherit as `WriterAgent(WriterAgentLifecycleMixin, WriterAgentFallbackStateMixin)` so the public entrypoint resolves from the lifecycle mixin first while still calling the already-extracted fallback/state helpers through normal `self` lookup;
- keep `__init__` and `_resolve_model()` in the main class because they are tiny identity/setup methods, not lifecycle orchestration worth isolating in this PRD;
- keep `_call_llm`, `_enforce_answer_compliance`, and `_enforce_mvp_free_dialogue_compliance` in the main class and out of scope;
- add a thin `_get_temperature_for_agent()` wrapper on `WriterAgent` so the old monkeypatch surface remains available after `_resolve_runtime_settings()` moves out of the class body;
- prove the move with before/after snapshots over the four required `write()` paths: `safety_success`, `safety_exception`, `normal_empty`, and `normal_exception`.

Consequences: the fourth `writer_agent.py` slice removes the class lifecycle spine from the god-file without changing public write-path behavior, while preserving both existing inheritance-based fallback dispatch and the accepted temperature monkeypatch seam. Future decomposition should now target `_call_llm` as the largest remaining active mixed-responsibility block before touching `writer_contract.to_prompt_context`.
## ADR-104 - self-bound writer_agent fallback/state helpers move by mixin, not by free-function rewrite

Status: accepted

Date: 2026-07-10

Delivery: PRD-047.42-APPLY-4 accepted in main commit `fadd43f`.

Context: PRD-047.42-APPLY-3 already removed the pure and static fallback edge of `writer_agent.py`, but the next smallest mapped slice was different in kind. The remaining target methods mutated `self.last_debug`, cached `self._client`, called each other through `self`, and still depended on class-owned fallback delegates plus `_resolve_model()`. Rewriting them into free functions would have forced broader call-site churn and increased the risk of accidental behavior drift for no architectural gain.

Decision:
- move the eight self-bound fallback/state methods into a dedicated `WriterAgentFallbackStateMixin`;
- move the three constants used only by those methods with them: `_COST_PER_1K_TOKENS`, `_RU_NAME_PATTERNS`, and `_EN_NAME_PATTERNS`;
- make `WriterAgent` inherit from the mixin instead of wrapping every call site or changing method signatures;
- keep `_resolve_model()` in the main class and let the mixin call it through normal inheritance lookup;
- keep slice-2 fallback delegates in `WriterAgent` because the moved methods still use them through `self`;
- keep `_PRACTICE_MARKERS` owned by `writer_agent.py` and expose it through a class attribute bridge rather than broadening this slice.

Consequences: the decomposition track can now cut real `self`-bound logic without changing the visible `WriterAgent` API. Future slices should continue with the smallest remaining non-giant class methods before touching `_call_llm`, `_enforce_answer_compliance`, or `writer_contract.to_prompt_context`.

## ADR-103 - writer_agent static fallback helpers move out behind thin delegates before self-bound fallback methods

Status: accepted

Date: 2026-07-10

Delivery: PRD-047.42-APPLY-3 accepted in main commit `b918b44`.

Context: PRD-047.42-APPLY-2 already removed the pure module-level edge of `writer_agent.py`, but the next safe slice still had a call-surface wrinkle: the remaining target helpers were formally `@staticmethod`, yet existing code still called part of them through `self._...`, and tests also referenced `WriterAgent._detect_language(...)` directly. A full call-site rewrite would increase PRD-local risk for no architectural gain.

Decision:
- move the bodies of the eight static fallback/helper methods into `writer_agent_fallback_helpers.py`;
- preserve the `WriterAgent` class-level API with thin `@staticmethod` delegates;
- keep internal `self._...` and class-level test call sites unchanged in this slice;
- keep `writer_agent_constants.py`, `writer_contract.py`, and the admin decomposition files out of scope;
- continue the writer-agent decomposition track from pure/static helpers toward small self-bound methods before touching `_call_llm` or `_enforce_answer_compliance`.

Consequences: the physical god-file reduction continues, but the behavioral surface remains low-risk and locally reviewable. Future slices can now focus on the smallest remaining self-bound fallback/name-continuity methods rather than re-litigating the static helper surface.

## ADR-102 - writer_agent decomposition starts with pure module-level helpers before any self-bound method moves

Status: accepted

Date: 2026-07-09

Delivery: PRD-047.42-APPLY-2 accepted in main commit `1051e68`.

Context: PRD-047.42 mapped `writer_agent.py` as the next major god-file risk after `admin_routes.py`, but unlike `admin_routes.py` it is a tightly coupled class-centered file. A broad first cut would blur behavior ownership across mutable agent state, runtime settings, prompt assembly, LLM IO, and compliance repair logic. The safest available edge was the tiny group of module-level pure helpers already defined outside `WriterAgent`.

Decision:
- begin the `writer_agent.py` apply track with the already-pure module-level helpers only;
- extract `_extract_literal_markdown_echo_request`, `_to_int`, `_to_float`, and `_contains_any` into a dedicated helper module;
- allow the dependent `_LITERAL_MARKDOWN_ECHO_PATTERNS` constant to move unchanged with the markdown-echo helper so the signatures and call sites stay stable;
- keep every `WriterAgent` method body unchanged in this slice;
- require before/after focused writer-suite evidence and direct tests for the extracted helpers;
- treat any unchanged baseline failure as inherited noise, not decomposition regression, if the failure set remains identical before vs after.

Consequences: the project now has a proven slice-first apply pattern for `writer_agent.py` without touching mutable method logic. Future decomposition should continue with pure/static helpers before moving `self`-bound methods, and leave `_call_llm` plus `_enforce_answer_compliance` for the end of the chain.

## ADR-101 - admin_routes decomposition stays behind a thin aggregator and exhaustive route snapshots

Status: accepted

Date: 2026-07-09

Delivery: PRD-047.42-APPLY accepted with warning in main commit `9822277`.

Context: PRD-047.42 produced an exact split map for `bot_psychologist/api/admin_routes.py`, but moving code out of the 2144-line file still carried two concrete risks: breaking the one external import contract used by `api/main.py`, or silently changing FastAPI route matching/behavior by altering registration order or import-time side effects.

Decision:
- realize the accepted map as `10` focused backend modules under `bot_psychologist/api/`;
- reduce `admin_routes.py` to a thin aggregator that still exports `admin_router` and `admin_router_v1`;
- preserve route registration order by importing the route-bearing modules in the original boundary-map sequence;
- prove behavior with exhaustive before/after snapshots over every registered admin route, not only representative handlers;
- normalize only volatile environment noise inside snapshots, such as backend start time, backend pid, and machine-local absolute data/thread/db paths;
- keep `api/main.py`, `writer_agent.py`, and `writer_contract.py` untouched in this PRD.

Consequences: the first real god-file apply step now has strong behavioral proof with `77/77` route cases and `0` differences. Remaining UI assertion debt is explicitly treated as pre-existing baseline noise unless a future PRD proves backend behavior drift.

## ADR-099 - Effective config truth is centralized, secrets are masked, and frozen env reads become constants only with proof

Status: accepted

Date: 2026-07-09

Delivery: PRD-047.41 accepted with warning in main commit `3211322`.

Context: PRD-047.39 inventoried `103` env/config flags and classified them into three coarse buckets, but that inventory still treated credential-like flags too similarly to ordinary tunables and left the runtime without one authoritative effective-config registry. PRD-047.40 then removed dead pipeline baggage, making it safer to consolidate config truth next. The main risks were leaking secret values into admin/debug payloads, silently changing runtime behavior while freezing env reads, or creating a second parallel config source of truth.

Decision:
- create one authoritative `effective_config_registry_v1` that covers all `103` inventoried flags;
- introduce an explicit `secret` status and export secret-like flags only as `{"is_set": bool}` rather than raw values;
- keep the registry integrated into the existing admin runtime effective payload path instead of creating a parallel truth surface;
- convert only the proven-frozen bucket-A env reads into literal constants with the same defaults;
- reclassify the already-editable bucket-B flags to `active_tunable` so registry labels match actual admin-editable behavior;
- defer `LEGACY_PIPELINE_ENABLED` as `retirement_candidate_deferred` until a separate admin/compat cleanup PRD rather than deleting diagnostic surfaces opportunistically;
- keep Writer behavior, retrieval, safety, DB/Chroma/source content, and runtime-path topology unchanged.

Consequences: config truth is now easier to audit and safer to expose in owner/admin surfaces. Secret leakage risk is reduced, registry labels match actual editable behavior, and the consolidation program can continue with narrower follow-ups instead of another broad config rewrite.

## ADR-097 - Consolidation starts with inventory and manifest-first hygiene, not runtime deletion

Status: accepted

Date: 2026-07-02

Delivery: PRD-047.39 accepted with warnings in main commit `3c9cf15faac3f0f31b49af58bad63939cfdbf78c`.

Context: PRD-047.38 accepted the current architecture with warnings and allowed the project to move out of the hotfix loop. The next risk is over-cleanup: deleting legacy-looking runtime code, flags, logs, or evidence without proof would make regressions harder to attribute.

Decision:
- PRD-047.39 is inventory-first: legacy code, env flags, god-files, logs, and git hygiene are classified before runtime deletion;
- active runtime code, Writer prompt, retrieval ranking, safety logic, DB/Chroma/source, and S7 behavior stay unchanged;
- fully merged remote branches and tracked backup artifacts may be removed from Git tracking because they are non-runtime and reversible from hashes/local files;
- markdown evidence in `TO_DO_LIST/logs` stays tracked;
- raw log untrack requires manifest-first classification and remains deferred unless explicitly approved from that manifest;
- dead runtime removal, flag consolidation, god-file splitting, admin UI dedup, and safety polish each require separate PRDs with their own gates.

Consequences: consolidation now has an evidence map and safe repo hygiene without mixing classification and runtime deletion. The project avoids another broad cleanup cycle that could hide regressions or break architect-session context continuity.

## ADR-096 - Owner pilot architecture gate is automated before consolidation

Status: accepted

Date: 2026-07-02

Context: PRD-047.37 froze the recovered baseline and produced a 12-scenario owner pilot brief, but the owner explicitly did not want to manually run and classify all 12 scenarios. Moving straight to cleanup without evidence would risk freezing a hidden trace/session/boundary regression as the new normal.

Decision:
- replace manual 12-scenario owner-pilot classification with a read-only automated evidence gate in PRD-047.38;
- grade only architecture/script invariants as PASS / WARNING / BLOCKER / INCONCLUSIVE;
- do not grade product polish, answer depth, preferred style, or bot smartness as blockers in this gate;
- reuse existing backend/session/trace/HF4 smoke tooling instead of adding a new runtime path, route, agent, or production mechanism;
- commit only sanitized reports with previews, counts, hashes, flags, and trace summaries;
- keep raw private logs, raw traces, screenshots, provider payloads, DB/cache artifacts, and helper browser artifacts out of Git.

Consequences: the project can move toward architecture consolidation on an audited baseline if the automated gate has no blockers. Any future answer-quality or DB/source improvements must be opened by a separate PRD rather than hidden inside consolidation cleanup.

## ADR-095 - Owner proceeds to cleanup/freeze despite accepted warnings

Status: accepted

Date: 2026-07-02

Context: HF4 restored fresh Web Chat trace/reload truth, HF5 restored direct concept follow-up selected-knowledge admission, and HF6 restored stable boundary proof for `no_internal_db` and `no_practice`. Remaining issues are real but bounded: old in-memory traces can expire after backend restart, greeting/contact wording may be too therapeutic, source exact-match coverage can be weak, shadow planner debug output may be noisy, and full pytest still has historical unrelated `_build_llm_prompts` debt.

Decision:
- stop the immediate hotfix loop by default;
- accept the current recovered runtime as a frozen owner-pilot baseline with warnings;
- document invariants, warnings, cleanup candidates, pilot scenarios, rollback rules, and transfer brief in PRD-047.37;
- do not use PRD-047.37 to change runtime behavior, Writer style, retrieval ranking, Bot_data_base, Chroma, registry, source documents, semantic-card authority, persistent trace storage, or route/agent architecture;
- create a future hotfix only if pilot evidence proves a hard blocker against the frozen invariants.

Consequences: the project now moves from hotfix recovery to owner pilot evidence and managed cleanup backlog. Known warnings are visible and accepted rather than hidden; the next architect should use `pilot_start_brief.md` and `invariants_register.md` as the baseline, not restart old debates or add speculative runtime layers.

## ADR-094 - Selected relevant concept knowledge must outrank generic no_clear_retrieval_need when no hard blocker applies

Status: accepted

Date: 2026-07-01

Context: PRD-047.36-HF4 restored owner trace truth, and private Chat 12 evidence then exposed a narrower runtime blocker: contextual concept follow-ups could already retrieve/select relevant knowledge and semantic cards, yet the existing grounding gate still classified the turn as `no_clear_retrieval_need`, leaving Writer payload at zero and semantic cards trace-only. The failure was not retrieval recall, not Writer style, and not DB/source coverage for the proven concept. It was a coordination defect inside the current path.

Decision:
- keep the canonical runtime path unchanged (`multiagent_adapter`);
- keep retrieval ranking, DB/Chroma/source content, model choice, and safety policy unchanged;
- do not add a dictionary, alias map, term-specific route, new agent, or new runtime path;
- promote a contextual turn to a bounded `direct_concept_followup` knowledge-admission path only when:
  - the turn is a direct concept follow-up or inherits the just-discussed concept;
  - selected relevant knowledge already exists;
  - no hard blocker such as `no_internal_db` applies;
- allow a minimal Writer-visible hidden knowledge package from already available selected knowledge / `memory_bundle.knowledge_rag_hits`;
- keep semantic cards advisory-only and Writer-can-ignore;
- keep public answers free of DB/chunk/card/trace language.

Consequences: the runtime now behaves coherently for the Chat 12 class: selected relevant concept knowledge is no longer left trace-only with `Writer Payload = 0` when no hard blocker exists. The repair stays generic and bounded inside the existing retrieval-to-Writer coordination path instead of creating a second policy system.

## ADR-093 - Fresh Web Chat trace restoration requires exact session-history persistence and reload-safe active chat restore

Status: accepted

Date: 2026-07-01

Context: PRD-047.36-HF3 made missing trace explicit, but owner/browser evidence still showed a hard blocker: fresh assistant turns in Web Chat could lose trace after reload, or reopen the wrong chat and show requested_turn_missing even when exact backend trace existed for the intended session. Audit showed the remaining defect was not Writer/retrieval authority. It was the delivery chain itself: streamed turns were not fully persisted under the exact chat session scope, browser identity was not fully communicated to backend, and the frontend could erase the persisted active chat id before session hydration completed.

Decision:
- keep the canonical runtime path unchanged (multiagent_adapter);
- persist streamed delivered turns into session history under the exact chat session_id;
- reuse one resolved turn number across debug trace save, SSE done payload, and session history persistence;
- send X-Device-Fingerprint from Web UI alongside X-Session-Id so backend identity resolution stays aligned with the browser session scope;
- preserve bot_active_chat_id through frontend hydrate/reload and do not clear it on initial empty mount before sessions load;
- keep strict exact trace lookup and candidate scoping from HF3;
- keep old-session-after-restart unavailable behavior explicit through debug_trace_expired_after_backend_restart;
- do not change Writer behavior, retrieval ranking, DB/Chroma/source content, model, semantic-card authority, or safety policy in this PRD.

Consequences: fresh Web Chat turns now keep exact trace through delivery, history, reload, and debug lookup, while old sessions after backend restart still fail honestly with a precise expired-trace reason. This is sufficient for `accepted_with_warning` under PRD-047.36-HF4 because fresh chats are fully restored and the old-session limitation is explicitly labeled instead of being confused with a fresh-trace failure. The next step is not another trace hotfix; it is rerunning the owner readiness freeze on the repaired baseline.
## ADR-092 - Exact trace lookup must stay candidate-scoped and missing trace must be explicit in owner/dev mode

Status: accepted

Date: 2026-06-30

Context: PRD-047.36-HF1 fixed wrong trace-to-bubble binding by threading explicit `turn_number`, but owner Chat 11 evidence showed a residual observability defect: after reload, some delivered assistant turns still had no visible trace/canvas. Audit showed two unsafe behaviors in the debug path: explicit `turn_index` lookup could silently fall back to latest trace, and store lookup could search beyond the requested candidate session keys. Frontend then suppressed the mismatch, leaving a silent missing-state.

Decision:
- keep the canonical runtime path unchanged (`multiagent_adapter`);
- keep exact trace lookup candidate-scoped to the requested session identity set;
- do not silently fall back to latest trace when `turn_index` is explicitly requested;
- add structured `trace_availability` metadata to the debug trace contract for both `available` and `unavailable` states;
- preserve owner/dev visibility by rendering an explicit unavailable-state under assistant turns when exact trace cannot be recovered;
- keep normal public mode free of this debug noise;
- do not change Writer behavior, retrieval ranking, DB/Chroma/source content, semantic cards, SSE protocol, or safety policy in this PRD.

Consequences: owner/debug reload behavior is now honest: every delivered assistant turn either resolves its exact trace or shows a structured unavailable reason with available turn indices. This closes the silent trace disappearance class without adding a new runtime path or mutating answer behavior.

## ADR-091 - Benign warning answers remain acceptable if no real failed checks remain, and chat trace must bind by explicit turn identity

Status: accepted

Date: 2026-06-30

Context: PRD-047.36 proved two coupled defects in the current pipeline: explicit `no_practice` turns could still collapse into a canned one-step answer, and even visibly acceptable benign turns could disappear from saved memory/history because `final_answer_acceptance_gate_v1` treated any `no_stub_repair_signal` warning as unsavable. Owner Web Chat evidence also showed trace/canvas mismatch after reload because frontend lookup still relied on fragile message-index inference.

Decision:
- keep the canonical runtime path unchanged (`multiagent_adapter`);
- preserve strict quarantine for real failed answers, but treat warning-only answers as acceptable when `failed_checks` is empty;
- add one narrow benign-warning calibration only for `no_stub_repair_signal` when the visible answer is already a bounded acceptable user-facing reply;
- keep no-practice repair inside the existing Writer compliance layer by removing forced canned one-step fallback on latest-turn no-practice/contact turns;
- thread explicit `turn_number` through:
  - SSE done payload
  - debug trace payload
  - history API response
  - frontend chat message state
  - trace-cache keys and trace lookup
- reject mismatched trace turns in the frontend instead of silently showing another turn's canvas.

Consequences: benign answers that are already acceptable no longer break saved-memory parity just because a retry signal exists, while real failed answers still quarantine. Web Chat trace/canvas/history now bind to explicit turn identity instead of positional reconstruction, reducing reload drift without adding a new runtime path, agent, retrieval policy, or DB/Chroma/source mutation.

## ADR-090 - Source-loss proof is mandatory for direct knowledge turns; empty explicit gates may recover only existing near-exact policy-allowed hits

Status: accepted

Date: 2026-06-30

Context: PRD-047.35 made public answers cleaner, but owner Chat 8 evidence still showed a deeper retrieval-truth gap: for direct knowledge turns the runtime could lose a source silently between raw retrieval, candidate selection, and Writer payload, and the owner trace could not prove where that happened.

Decision:
- keep the canonical runtime path unchanged (`multiagent_adapter`);
- expose raw retrieval evidence through `raw_hit_summaries`;
- add `source_chunk_match_trace_v1` in the existing writer-context/runtime-trace chain so owner/debug surfaces can prove:
  - raw source match
  - runtime candidate match
  - payload match
  - `loss_stage`
  - `loss_reason`
- allow one bounded recovery only inside the existing writer-context packaging path:
  - only when the explicit retrieval gate is empty;
  - only when the current turn already allows KB-visible direct knowledge grounding;
  - only when an existing policy-allowed hit in `memory_bundle.knowledge_rag_hits` has a near-exact current-turn match;
  - no dictionary, no alias map, no new route, no new agent, no DB/source/Chroma mutation.

Consequences: direct-match silent loss is now observable and repairable inside the current runtime without hiding true missing-source cases. Owner review can now distinguish source absence from candidate-selection failure, and future work can move either to delivery integrity or separate source-preparation PRDs instead of ad-hoc runtime hacks.

## ADR-089 - Public user mode treats internal knowledge as hidden competence, not a conversation topic

Status: accepted

Date: 2026-06-26

Context: PRD-047.34 repaired latest-turn authority, but owner live evidence still showed a product-level mismatch: even when retrieval/payload boundaries were technically correct, public answers could still sound like they were reporting from internal storage or explaining too much theory. The next repair had to stay inside the current runtime and make the product speak from competence rather than about its internals.

Decision:
- keep the canonical runtime path unchanged (`multiagent_adapter`);
- add `hidden_knowledge_competence_v1` inside the existing writer-context/runtime-trace chain;
- treat internal KB/semantic-card evidence as Writer-only hidden competence in public user mode, not as user-facing DB/chunk/system talk;
- preserve explicit direct-source/debug questions as diagnosable exceptions without letting them redefine the ordinary product path;
- bias ordinary answers toward:
  - one main mechanism
  - what that mechanism protects
  - at most one next question or one next step
- use Wake as a depth/mechanism reference only, never as a style template;
- forbid any new route, new agent, broad KB default, Bot_data_base mutation, Chroma mutation, or semantic-card expansion in this layer.

Consequences: the product now sounds more like a competent specialist and less like a system describing its storage. Runtime trace keeps the hidden-competence evidence visible for owner review, while public answers remain free of internal-language leakage. Remaining work shifts to bounded live-shape polish and readiness gating, not architecture expansion.

## ADR-088 - Latest user turn is the primary answer target; previous must-answer/open loop is context unless explicitly continued

Status: accepted

Date: 2026-06-26

Context: after PRD-047.30 to PRD-047.33, the runtime already reduced broad KB authority and improved answer-shape compactness, but owner live evidence still showed a deeper behavioral failure: after a previous KB or practice topic, a new human latest turn like `РјРЅРµ С‚СЏР¶РµР»Рѕ, РїСЂРѕСЃС‚Рѕ СЃРєР°Р¶Рё РїРѕ-С‡РµР»РѕРІРµС‡РµСЃРєРё` could still be answered as continuation of the old internal task.

Decision:
- keep the canonical runtime path unchanged (`multiagent_adapter`);
- treat the latest non-empty user turn as the default answer target inside `final_answer_directive_v1`;
- keep previous unanswered/open-loop state visible as `previous_must_answer`, but demote it to context-only unless explicit continuation is detected;
- expose latest-turn authority explicitly through:
  - `current_user_request`
  - `must_answer_source`
  - `previous_must_answer_demoted`
  - `previous_must_answer`
  - `explicit_continue_previous_detected`
  - `answer_target`
  - `writer_contact_mode`
- preserve higher-priority overrides for safety, direct KB/source, explicit practice, explicit no-practice, and no-internal-db boundaries;
- allow `free_writer_contact` as a soft contact-mode answer profile inside the current runtime, not as a new route or a new agent;
- suppress legacy advisory micro-step leakage when the latest turn forbids practice or requests human contact.

Consequences: the runtime now answers the latest user turn first and treats older internal tasks as context unless the user explicitly continues them. This reduces stale-task pressure on Writer without expanding architecture, retrieval authority, or DB/Chroma scope. Future work should refine remaining style polish inside this chain, not create another authority subsystem.

## ADR-087 - Answer shape is calibrated through soft final-directive profiles, not a new runtime route

Status: accepted

Date: 2026-06-25

Context: PRD-047.32 proved that ordinary owner-pilot verbosity was no longer mainly a KB-leak problem: Writer payload was often `0`, while some answers still sounded too methodical or lecture-like. The repository needed a narrower answer-shape control inside the current runtime rather than a new style-agent, a new route, or DB mutation.

Decision:
- keep the canonical runtime path unchanged (`multiagent_adapter`);
- add soft `answer_shape_profile` selection inside `final_answer_directive_v1` rather than introducing a new subsystem;
- pass the selected profile and profile notes through `WriterContract` into Writer prompt assembly and `runtime_trace_summary_v1`;
- treat profiles as soft shape hints only, not a hard rule engine:
  - `contact_brief`
  - `ordinary_explanation_compact`
  - `concrete_situation_compact`
  - `bounded_practice`
  - `no_internal_db_compact`
  - `direct_kb_grounded_compact`
  - `safety_grounding_compact`
- preserve higher-priority boundaries for safety, explicit practice, explicit no-internal-db, and direct KB/source requests;
- forbid any new agent, new runtime path, broad KB re-enable, Bot_data_base mutation, Chroma mutation, or thin-spine production apply in this calibration layer.

Consequences: answer-shape steering now lives in the existing final-directive -> Writer prompt -> runtime-trace chain, which is easier to audit and cheaper to evolve than another routing layer. Future work should repair remaining shape conflicts inside that chain, not expand architecture.

## ADR-086 - Latest explicit practice request outranks stale must-answer, while Writer grounding stays narrow

Status: accepted

Date: 2026-06-24

Context: PRD-047.30 correctly hid broad Writer-visible KB/semantic-card grounding on ordinary support turns, but live `Р§РђРў_РЎ_Р‘РћРўРћРњ2` evidence showed a new failure class: the user explicitly asked for a practice to build non-reactivity, while the runtime followed stale `must_answer` state and returned an unrelated generic productivity fallback (`РѕС‚РєСЂРѕР№ Р·Р°РґР°С‡Сѓ / 5 РјРёРЅСѓС‚`).

Decision:
- keep the canonical runtime path unchanged (`multiagent_adapter`);
- let the latest explicit practice request override stale unanswered-question / `must_answer` carry-over in the existing dialogue-act, unanswered-question, and final-directive layers;
- preserve current-thread continuity for explicit practice follow-ups after a concrete situation discussion, even if lexical overlap is low;
- allow Writer-visible grounding for explicit practice turns only through a narrow chunk-type allowlist: `practice`, `dialogue_move`, `anti_pattern`, and `safety`;
- keep broad KB/concept/mechanism grounding hidden by default on ordinary support turns and on explicit practice turns unless the chunk type is in that narrow allowlist;
- expose the explicit-practice mode through compact trace/runtime summary notes without adding a new route, new agent, DB mutation, Chroma mutation, or thin-spine production apply.

Consequences: the latest explicit user request now has a stronger bounded authority than stale carry-over state for this practice-turn class, while PRD-047.30's anti-noise boundary remains intact. Future work should target remaining fallback/prompt verbosity and runtime-truth noise rather than creating another routing subsystem.

## ADR-085 - Semantic chunk cards are advisory local Writer grounding, not retrieval or KB authority

Status: accepted

Date: 2026-06-19

Context: PRD-047.26-HF1 stabilized live dialogue quality enough to start a minimal DB-track pilot, but the repository still lacked a small, reviewable way to pass curated semantic guidance into Writer without mutating Bot_data_base, Chroma, retrieval ranking, or Writer authorship.

Decision:
- add a bounded local knowledge pack `semantic_cards_pilot_v1` with 10-20 curated cards only;
- keep the pilot behind `SEMANTIC_CARDS_PILOT_ENABLED`, default `false`, and restrict effective enablement to `APP_ENV in {local, dev, test}`;
- select at most 3 cards from the current turn using simple deterministic overlap and explicit suppression for greeting/contact or `no theory` turns;
- feed selected cards only into the existing `writer_kb_payload_v1` enrichment path;
- expose `semantic_cards_pilot_trace_v1` in runtime/debug/API as observability, not authority;
- preserve `writer_can_ignore=true`, keep Writer as final answer author, and forbid DB schema mutation, Chroma reindex, retrieval-ranking rewrite, overlay apply, registry mutation, or new runtime paths in this PRD.

Consequences: the repository now has a minimal semantic-card pilot surface that can be evaluated in live dialogue without changing retrieval authority or KB truth. Future work should focus on owner/live review of answer quality before any broader DB-track or semantic-card graduation PRD.

## ADR-084 - Retrieval query assembly is current-turn-focused by default on local developer runtimes

Status: accepted

Date: 2026-06-18

Context: PRD-047.23 proved that the dominant retrieval defect was no longer source/chunk corruption but query assembly pollution: standalone knowledge questions could inherit the previous user topic, long explicit asks could duplicate themselves, and truncated legacy queries could end mid-word, pulling RAG away from the correct sections even when the expected source already existed.

Decision:
- add isolated deterministic `retrieval_query_builder.py` with `current_turn_focus_v1` query assembly;
- enable `RETRIEVAL_CURRENT_TURN_FOCUS_ENABLED` by default for `APP_ENV in {local, dev, pilot, test}` while keeping production-style runtimes conservative unless explicitly enabled;
- treat the current user question as the primary retrieval authority for standalone knowledge asks;
- forbid naive concatenation of the previous user question into the retrieval query by default;
- allow only compact contextualization for genuine elliptical follow-ups, using inherited topic or last assistant offer summary with explicit trace reasons;
- collapse duplicate fragments, avoid mid-word truncation, and preserve a warning-only legacy fallback path;
- expose `retrieval_query_build_trace_v1` through runtime/debug/API/Web Trace;
- keep retrieval ranking, Writer authority, Bot_data_base content, processed chunks, registry, live metadata, and Chroma unchanged within this PRD.

Consequences: retrieval execution now has an explicit current-turn-focused assembly layer that can prove why the final query was used. The repository can separate query-assembly defects from source-content defects, while any future work on overlay live evidence, retrieval ranking, or trace-schema cleanup stays in separate PRDs.

## ADR-083 - Writer receives structured KB payload instead of blind truncated snippets

Status: accepted

Date: 2026-06-17

Context: PRD-047.21 and PRD-047.22 proved the structured Writer KB payload path itself, but PRD-047.22-HF1/HF2 exposed a parity problem: managed smoke could show `writer_kb_payload_v1` while ordinary pilot/manual Web Chat startup could still drift into legacy semantic-hit fallback because effective runtime config was not visible as a single source of truth.

Decision:
- keep retrieval selection authority exactly where it already is;
- replace the enabled Writer-visible KB delivery path with `writer_kb_payload_v1`, an isolated structured payload over already-selected hits;
- make excerpting sentence/paragraph-aware and trace every truncation decision through `writer_kb_payload_trace_v1`;
- treat `writer_kb_payload_v1` as the canonical primary path for pilot/manual Web Chat and expose effective config source through runtime/admin/debug trace;
- resolve `WRITER_KB_PAYLOAD_ENABLED` from one effective-config source, with `APP_ENV in {local, dev, pilot, test}` enabling `default_local` and production-style runtimes staying gated unless explicitly enabled;
- preserve legacy semantic hits only as emergency fallback, with explicit `fallback_reason`, `fallback_is_primary`, and warning visibility in trace whenever fallback becomes primary;
- allow future overlay metadata enrichment only as optional same-hit enrichment and keep it disabled by default;
- keep Writer as the only author of final user-facing text; payload metadata is grounding, not command;
- forbid retrieval-ranking changes, executed-query mutation, live metadata apply, processed-block mutation, registry mutation, and Chroma reindex inside this PRD.

Consequences: Writer now receives selected knowledge through one canonical structured path in pilot/manual Web Chat as well as managed smoke, and the repository can prove whether a turn used the primary payload path or an emergency fallback. Runtime authority boundaries remain unchanged: retrieval, Chroma, registry, processed blocks, and live metadata are untouched. The next step can evaluate live overlay + payload evidence only after this parity truth is present.

## ADR-082 - Accepted overlay may be visible in runtime trace before gaining retrieval authority

Status: accepted

Date: 2026-06-16

Context: `PRD-047.20` produced a useful accepted-overlay preview with strong offline retrieval evidence, but the project still lacked any runtime evidence showing where that overlay would help or stay noisy under real multiagent requests. Moving directly to retrieval authority or metadata apply would skip the required observability boundary.

Decision:
- allow accepted overlay artifacts to be loaded read-only by runtime only for sanitized shadow trace;
- keep default flag off via `OVERLAY_SHADOW_TRACE_ENABLED=false` and `OVERLAY_SHADOW_TRACE_MODE=trace_only`;
- expose overlay shadow only in debug/API/Web Trace surfaces;
- keep Writer as the only author of final user-facing text;
- forbid overlay influence on executed retrieval query, semantic hits, context assembly, WriterContract, Writer prompt, final answer logic, BotDB registry, processed blocks, and Chroma until a separate future PRD explicitly grants that authority;
- require later allowlisted live evidence and separate governance gates before any broader runtime activation.

Consequences: the repository now has a safe runtime observability layer for curated overlay evidence without changing retrieval execution or answer behavior. Trace visibility is explicitly not retrieval authority, not Writer authority, and not approval to apply overlay metadata live.

## ADR-080 - Curated overlay preflight is read-only planning, not permission to apply metadata

Status: accepted

Date: 2026-06-16

Context: `PRD-047.18` introduced curated overlay preview artifacts, but even accepted fields remained fixture-only review evidence. The next required step was to prove the project can map accepted fields onto future metadata targets and show diff previews without mutating processed blocks, live metadata, Chroma, retrieval, or Writer runtime.

Decision:
- add a read-only `mechanism_metadata_apply_preflight_v1` workflow over `mechanism_metadata_curated_overlay_preview_v1`;
- validate overlay intake, candidate/block consistency, future field mapping, and diff preview under `overlay_only_no_write`;
- treat `fixture_only=true` and lack of real human-reviewed decisions as expected blockers for live apply readiness;
- keep `ready_for_live_apply=false`, `ready_for_chroma_reindex=false`, and `ready_for_runtime_visibility=false` for fixture overlays;
- forbid using dry-run apply plans as runtime authority, live metadata writes, or implicit approval for future Chroma/apply PRDs.

Consequences: the repository now has an explicit preflight layer that can explain what would change and why it still must not be applied. A later PRD needs real non-fixture human-accepted overlay before any apply/reindex planning can move beyond expected blockers.

## ADR-079 - Manual review decisions remain curated overlay previews, not live KB truth

Status: accepted

Date: 2026-06-16

Context: `PRD-047.17` produced 80 real-source enrichment candidates over Kuznica, but the project still needed an explicit human-review workflow before any candidate field could be considered for future KB apply or retrieval/runtime experiments.

Decision:
- add `mechanism_metadata_review_decision_v1` as a separate review contract over PRD-047.17 candidates;
- generate review queue, pending decision template, validation report, fixture-only decisions, and `mechanism_metadata_curated_overlay_preview_v1`;
- allow accepted fields to exist only inside curated overlay preview artifacts with `live_apply_allowed=false` and `safe_to_apply_to_live_metadata=false`;
- require a separate explicit apply/reindex PRD before curated decisions can affect live metadata, Chroma, retrieval, or Writer-visible behavior;
- keep PRD-047.18 offline-only: no Writer/runtime mutation, no Chroma reindex, no DB apply, and no new UI/runtime authority.

Consequences: the repository now has a governed acceptance workflow for enrichment candidates, but accepted fields remain review evidence only. Live KB truth, retrieval authority, and Writer behavior are unchanged until a later apply/preflight PRD explicitly authorizes them.

## ADR-078 - Offline enrichment candidates are manual-review inputs, not live KB truth

Status: accepted

Date: 2026-06-16

Context: after `PRD-047.16`, the project had stable mechanism-aware metadata normalization, but real Kuznica chunks still lacked richer source-grounded summary/use-when/avoid-when/contraindication signals. The next step needed better offline candidate quality without changing Writer behavior, retrieval authority, or live KB truth.

Decision:
- add `mechanism_metadata_enrichment_candidate_v1` as an offline candidate contract on top of `MechanismAwareChunkMetadata v1`;
- generate deterministic candidates, source profile, chapter coverage, and manual-review pack over the real Kuznica processed source;
- keep every enrichment candidate as `candidate_only`, `manual_review_required=true`, and `safe_to_apply_automatically=false`;
- forbid applying candidate fields to live metadata, WriterContract, runtime routing, or Chroma within this PRD;
- allow an optional provider-backed `llm-candidate` interface only behind explicit confirmation, with sanitized artifacts and no raw provider payload committed.

Consequences: the repository now has a richer offline review surface for metadata quality, while KB truth, Writer authority, retrieval runtime behavior, and production boundaries remain unchanged. The next step moves to curated acceptance workflow rather than direct activation.

## ADR-077 - Mechanism-aware chunk metadata is semantic guidance, not deterministic routing

Status: accepted

Date: 2026-06-15

Context: after `PRD-047.15-HF2-R2`, Hybrid Retrieval Planner visibility was in place, but retrieval quality was still limited by legacy BotDB metadata that could not express mechanism depth, visibility, quote policy, contraindications, or writer-facing boundaries in a stable audit-ready contract.

Decision:
- add `MechanismAwareChunkMetadata v1` in the existing `Bot_data_base/knowledge_governance` layer instead of creating a parallel runtime subsystem;
- normalize legacy governed blocks into the new schema through a backward-compatible adapter and preserve unknown fields in `legacy_metadata` / `extra_metadata`;
- treat metadata as semantic guidance for retrieval/planner/context assembly audits only;
- forbid using mechanism markers, user markers, or depth labels as deterministic runtime routing rules;
- keep Writer as the only author of user-facing text;
- keep the PRD read-only: no DB mutation, no Chroma reindex, no Writer-path activation, and no new LLM enrichment agent.

Consequences: the codebase now has a stable offline metadata foundation and audit vocabulary for later enrichment/evaluation PRDs, while live runtime authority and retrieval execution remain unchanged.

## ADR-076 - Hybrid Retrieval Planner owns metadata-only query-before-RAG, not Writer authority

Status: accepted

Date: 2026-06-11

Context: after PRD-047.15 and HF1, retrieval still had a structural flaw: the runtime could compose a better retrieval query in trace, while `MemoryRetrievalAgent` had already executed RAG from legacy `_build_rag_query(...)`. Complex/mixed cases also risked pushing more and more domain-specific composer heuristics into production logic.

Decision:
- add `hybrid_retrieval_planner_v1_r1` as a metadata-only planner inside the existing multiagent runtime path;
- keep deterministic universal retrieval gates for simple cases and allow optional strict-JSON LLM planning only for complex/low-confidence cases;
- approve retrieval metadata before RAG execution and pass it into `MemoryRetrievalAgent.assemble(..., retrieval_plan=...)`;
- preserve Writer as the only author of user-facing text; planner output must never become a reply draft;
- expose planned query, executed query, query-before-RAG proof, planner validity/fallback, mode, chunk-type hints, and mechanism hints in trace/debug/API;
- keep conservative defaults (`shadow` safe mode, no broad rollout, no normal-user activation) and forbid production domain-specific hardcoded concept expansions in the composer/planner layer.

Consequences: retrieval execution is now observable and auditable as a first-class pre-RAG contract; live `apply` validation can prove planned and executed queries match when enabled; Writer freedom and governance boundaries remain intact; further work shifts from backend plumbing to UI visibility sync and later KB chunk metadata quality.

## ADR-074 - Retrieval query composition is contextual and advisory, not literal-last-message search

Status: accepted

Date: 2026-06-08

Context: after summary routing and no-stub repairs, retrieval remained the next bottleneck: short contextual replies such as `??, ??????` can require the previous assistant offer topic, while summary/contact/support turns often should not retrieve external KB at all.

Decision:
- add deterministic `contextual_retrieval_query_composer_v1` as an internal agent-like layer;
- compose retrieval need, action, query source, compact query terms, and writer inclusion policy from dialogue context, not only the current user utterance;
- suppress RAG when chunks would be noise for summary/contact/close/support/safety/one-step turns;
- expose composer payload through retrieval decision, writer context package, WriterContract prompt context, and trace/debug;
- keep Writer as final answer author;
- do not create user-facing text, canned replies, a new LLM agent, DB/KB/frontend mutation, or a separate runtime path.

Consequences: retrieval becomes contextual and observable while remaining advisory and deterministic; live calibration is delegated to PRD-047.15-HF1.

## ADR-072 - Explicit summary requests own route and obligation without canned answers

Status: accepted

Date: 2026-06-08

Context: PRD-047.14 and HF1.2 left a focused risk where explicit recap/summary requests could be mistaken for confirmation of the previous assistant offer or handled by static Writer summary text.

Decision:
- explicit current-conversation summary requests resolve to `dialogue_act=summary_request` before last-offer confirmation;
- the answer obligation is `summarize_current_conversation`;
- `final_answer_directive_v1` exposes summary metadata to Writer while preserving Writer authorship;
- Writer must not create a canned summary replacement;
- `final_answer_acceptance_gate_v1` blocks reconfirmation/last-offer misanswers and recommends retry/quarantine without producing replacement text;
- no new LLM agent, runtime path, KB/governance authority, frontend path, or rollout activation is introduced.

Consequences: summary turns can be tracked and retried honestly without contaminating last-offer state or healthy context memory.

## ADR-071 - PRD-047.13-HF1 closes active cleanup noise without runtime mutation

Status: accepted

Date: 2026-06-08

Context: PRD-047.13 produced a cleanup inventory and proved runtime non-mutation, but active documentation still contained stale next-PRD references, living-doc metadata gaps, and potentially misleading profile/admin labels. Historical empty artifacts and encoding warnings also needed explicit closure classification.

Decision:
- PRD-047.13-HF1 may change docs, cleanup reports, manifests, placeholder explanations, and Web Admin help labels only;
- `safe_guided`, `mvp_free_dialogue`, and `free_dialogue_default` are documented as presets/aliases of `unified_dialogue_policy_v2`, not separate systems;
- historical artifacts remain preserved or manifest-classified; active empty/noisy artifacts must be closed;
- Writer, Orchestrator, Dialogue Act Resolver, Final Answer Acceptance Gate, RAG/Chroma, prompt behavior, Diagnostic Center authority, production flags, and runtime paths remain unchanged.

Consequences: PRD-047.13-HF1 is the final cleanup closure before `PRD-047.14 - Live Dialogue Quality Polish / Human Reference Calibration v1`.

## ADR-070 - PRD-047.13 cleanup boundary preserves runtime baseline

Status: accepted

Date: 2026-06-05

Context: after PRD-047.12-HF1, the unified dialogue runtime has an accepted engineering baseline, but the repository still contains historical PRDs, logs, reports, admin labels, and docs that can be confused with active runtime instructions.

Decision:
- PRD-047.13 is limited to inventory, classification, docs truth sync, admin surface inventory, and manifest-backed cleanup reporting;
- Writer, Orchestrator, Final Answer Acceptance Gate, Stale Stub Detector, Dialogue Act Resolver, RAG/Chroma, prompt behavior, and Diagnostic Center authority remain out of scope;
- archive/delete actions require explicit manifests;
- `production_ready=false`, `broad_rollout_allowed=false`, and `normal_user_activation_allowed=false` remain invariant.

Consequences: cleanup evidence lives under `TO_DO_LIST/logs/PRD-047.13/`; live dialogue quality work moves to PRD-047.14.

## ADR-068 - Writer-first prompt assembly for MVP profile

Status: accepted

Date: 2026-06-01

Context: PRD-047.10/HF cycles left residual conflicts where legacy prompt blocks (`writer_move`, `diagnostic_card`, `active_line`, `response_planner`) still appeared as imperative commands and repeatedly produced stale regulate-style stub answers in live dialogue.

Decision:
- add deterministic `final_answer_directive_v1` as single conflict-resolved command block for Writer in `mvp_free_dialogue`;
- keep Diagnostic Center / Planner / Active Line / Diagnostic Card as advisory context providers for MVP profile;
- keep minimal safety/privacy/no-diagnosis boundaries as hard limits;
- expose writer-first assembly and role fields in admin runtime effective payload + live evidence export;
- add strict stale-stub detector for regression checks across answer payloads and artifacts.

Consequences:
- no new LLM agent and no new runtime path were added;
- governance authority fields and Chroma index were not mutated;
- live acceptance remains explicitly blocked until runtime profile activation and real web markdown smoke pass are green.

## ADR-069 - HF3 repairs concrete formula-stub answers at answer level, not by adding new runtime authority

Status: accepted

Date: 2026-06-04

Context: after HF2, real owner feedback still showed a residual class where concrete user situations could receive a generic formula opening like `РЎРµР№С‡Р°СЃ РїРѕР»РµР·РЅРµРµ РЅРµ СѓРїСЂР°Р¶РЅРµРЅРёРµ...`, and bare gratitude turns could still surface misleading deterministic `hypo/explore` signals in trace.

Decision:
- add a lightweight concrete-answer-fit heuristic (`concrete_answer_fit_v1`) and contextual no-practice rewrite only for concrete formula-stub failures;
- keep Writer freedom intact in MVP profile and do not add a new guard, mode, runtime path, or LLM agent;
- repair deterministic gratitude/close handling so simple `РЎРїР°СЃРёР±Рѕ.` maps to `intent=contact` and `nervous_state=window`;
- revalidate browser/admin proof on real `localhost:3000` and capture explicit reset/memory/admin inventory artifacts;
- treat docs/encoding hygiene as part of the runtime truthfulness boundary for this cycle.

Consequences:
- the fix remains observability-friendly and local to answer-level/runtime evidence without broadening authority;
- concrete situation answers are less likely to pass through stale generic mechanism stubs;
- localhost UX and docs truthfulness are now part of the same stabilization evidence pack before `PRD-047.12`.
## ADR-065 - Planner Drift Guard is observe-only runtime quality monitor

Status: accepted

Context: РїРѕСЃР»Рµ PRD-047.5-HF1 РѕСЃС‚Р°РІР°Р»СЃСЏ СЌРєСЃРїР»СѓР°С‚Р°С†РёРѕРЅРЅС‹Р№ СЂРёСЃРє runtime drift (model/provider/prompt/runtime variability) РґР°Р¶Рµ РїСЂРё Р·РµР»С‘РЅС‹С… РєР°Р»РёР±СЂРѕРІРѕС‡РЅС‹С… РїСЂРѕРіРѕРЅР°С….

Decision: РІРІРµРґС‘РЅ РґРµС‚РµСЂРјРёРЅРёСЂРѕРІР°РЅРЅС‹Р№ `planner_drift_guard_v1` РєР°Рє observability-first СЃР»РѕР№:
- СЃРІРµСЂСЏРµС‚ `response_planner` Рё `final_answer` РЅР° РєР°Р¶РґРѕРј С…РѕРґРµ;
- РїРёС€РµС‚ `status/severity/flags` РІ trace/debug;
- РІРµРґС‘С‚ rolling summary counters (in-memory, max window=100);
- РїСѓР±Р»РёРєСѓРµС‚ read-only runtime block РІ admin effective;
- РёСЃРїРѕР»СЊР·СѓРµС‚СЃСЏ РґР»СЏ dry/direct/live replay regression Р°СЂС‚РµС„Р°РєС‚РѕРІ.

Consequences:
- drift guard РЅРµ Р±Р»РѕРєРёСЂСѓРµС‚ Рё РЅРµ РїРµСЂРµРїРёСЃС‹РІР°РµС‚ РїРѕР»СЊР·РѕРІР°С‚РµР»СЊСЃРєРёР№ РѕС‚РІРµС‚;
- drift guard РЅРµ СЏРІР»СЏРµС‚СЃСЏ РЅРѕРІС‹Рј LLM-Р°РіРµРЅС‚РѕРј;
- governance authority (`chunk_type`, `allowed_use`, `safety_flags`) РЅРµ РјРµРЅСЏРµС‚СЃСЏ;
- runtime quality drift СЃС‚Р°РЅРѕРІРёС‚СЃСЏ РЅР°Р±Р»СЋРґР°РµРјС‹Рј Р±РµР· broad rollout / production activation.
## ADR-066 - Guided Live Feedback Protocol is evidence loop, not runtime mutation

Status: accepted

Context: РїРѕСЃР»Рµ runtime observability (PRD-047.6) РѕС‚СЃСѓС‚СЃС‚РІРѕРІР°Р» СЃС‚СЂСѓРєС‚СѓСЂРёСЂРѕРІР°РЅРЅС‹Р№ РїСЂРѕС†РµСЃСЃ Р¶РёРІРѕРіРѕ РїРѕР»СЊР·РѕРІР°С‚РµР»СЊСЃРєРѕРіРѕ С‚РµСЃС‚РёСЂРѕРІР°РЅРёСЏ Рё СЃРІСЏР·РєРё human feedback СЃ trace/debug.

Decision: РІРІРµРґС‘РЅ guided live testing protocol v1 СЃ СЃР°РЅРёС‚РёР·РёСЂРѕРІР°РЅРЅС‹Рј feedback capture/storage Рё summary workflow:
- feedback С…СЂР°РЅРёС‚СЃСЏ РєР°Рє file-based sanitized artifacts;
- feedback СЃРІСЏР·С‹РІР°РµС‚СЃСЏ СЃ compact trace summary (`active_line`, `response_planner`, `planner_drift_guard`, `writer`);
- runtime/admin/web РѕС‚РѕР±СЂР°Р¶Р°СЋС‚ read-only guided live testing status;
- feedback РЅРµ РёР·РјРµРЅСЏРµС‚ runtime РїРѕРІРµРґРµРЅРёРµ Р°РІС‚РѕРјР°С‚РёС‡РµСЃРєРё.

Consequences:
- feedback СЃС‚Р°РЅРѕРІРёС‚СЃСЏ first-class evidence РґР»СЏ СЃР»РµРґСѓСЋС‰РёС… PRD;
- Writer hard constraints РЅРµ СѓСЃРёР»РёРІР°СЋС‚СЃСЏ РІ feedback layer;
- `final_answer` РЅРµ РїРµСЂРµРїРёСЃС‹РІР°РµС‚СЃСЏ Рё РЅРµ Р±Р»РѕРєРёСЂСѓРµС‚СЃСЏ;
- РЅРѕРІС‹Р№ LLM-Р°РіРµРЅС‚ РЅРµ РґРѕР±Р°РІР»СЏРµС‚СЃСЏ, governance authority РЅРµ РјСѓС‚РёСЂСѓРµС‚СЃСЏ.

## ADR-066 Amendment - Dialogue profiles are presets over one unified adaptive policy surface

Status: accepted

Date: 2026-05-29

## PRD-047.12-HF1 Final Answer Acceptance Gate

Decision: add `final_answer_acceptance_gate_v1` after Writer and Validator, before unanswered-question closure, last-offer seeding, and healthy context memory write.

Rationale: PRD-047.12 unified the architecture, but live evidence showed false positives where stale/generic answers could be accepted as answered. The fix is a truth gate and quarantine layer in the same runtime path, not a new mode, LLM agent, or static answer factory.

Consequences: failed final answers can trigger one Writer retry with gate feedback. If still failed, the answer is quarantined from healthy state while trace/debug exposes status and failed checks. Diagnostic Center, Planner, and Active Line remain advisory-only.

Context: `mvp_free_dialogue` introduced higher Writer freedom, but residual conflicts remained when old planner/diagnostic constraints and context truncation still dominated prompt behavior.

Decision:
- keep single multiagent runtime path (no duplicated orchestrator/writer/planner);
- treat `safe_guided` and `mvp_free_dialogue` as presets of one `dialogue_policy` authority resolver;
- enforce authority order: minimal safety > explicit user request > knowledge/concept need > writer freedom > planner/diagnostic advisory;
- preserve Writer context by recency with profile-specific budgets, instead of fixed `[:2000]` prefix slicing;
- keep planner drift guard observe-only (no blocking/rewrite of final answer).

Consequences:
- mode switching becomes parameterized behavior, not architecture branching;
- explanation/overview/practice requests can expand in MVP profile without removing minimal safety baseline;
- runtime/admin/trace can expose one coherent effective policy contract.

## ADR-067 - MVP human-like writer autonomy uses policy-level constraint resolution, not new guard/runtime branch

Status: accepted

Date: 2026-06-01

Context: after PRD-047.9 architectural unification, live owner feedback still showed formal/over-constrained answers in `mvp_free_dialogue` for direct concrete requests, dissatisfaction repair, and summary requests.

Decision:
- add `human_like_answer_policy` and `constraint_resolution` to unified effective `dialogue_policy`;
- keep authority order within single runtime path (`minimal safety > explicit user request > live dialogue pragmatics > knowledge/concept need > writer autonomy > planner advisory`);
- treat legacy restrictive constraints as advisory-overridable metadata in MVP profile;
- expose human-like/constraint-resolution metadata in admin effective and trace payloads.

Consequences:
- no new LLM agent and no new runtime path were introduced;
- no blocking evaluator or final-answer auto-rewrite layer was added;
- writer keeps freedom in MVP while minimal safety baseline remains intact;
- observability of constraint overrule reasons is explicit and auditable.

## ADR-001 - Multiagent-only runtime

Status: accepted

Context: cascade/legacy path СЃРѕР·РґР°РІР°Р» СЂР°Р·РјС‹С‚С‹Рµ РєРѕРЅС‚СЂР°РєС‚С‹ Рё РЅРµРїСЂРµРґСЃРєР°Р·СѓРµРјСѓСЋ РґРёР°РіРЅРѕСЃС‚РёРєСѓ.

Decision: runtime СЂР°Р±РѕС‚Р°РµС‚ С‡РµСЂРµР· multiagent-only orchestration СЃ СЏРІРЅС‹Рј СЂР°Р·РґРµР»РµРЅРёРµРј СЂРѕР»РµР№.

Consequences: РІС‹С€Рµ РєРѕРЅС‚СЂРѕР»РёСЂСѓРµРјРѕСЃС‚СЊ trace Рё РїСЂРѕС‰Рµ quality gating.



## ADR-002 - Writer is not the whole diagnostic system

Status: accepted

Context: РїРѕРїС‹С‚РєР° РІРѕР·Р»РѕР¶РёС‚СЊ РґРёР°РіРЅРѕСЃС‚РёРєСѓ С†РµР»РёРєРѕРј РЅР° Writer СѓС…СѓРґС€Р°РµС‚ РІРѕСЃРїСЂРѕРёР·РІРѕРґРёРјРѕСЃС‚СЊ.

Decision: РґРёР°РіРЅРѕСЃС‚РёРєР° СЂР°СЃРїСЂРµРґРµР»СЏРµС‚СЃСЏ РјРµР¶РґСѓ State Analyzer, Thread Manager, Diagnostic Card Рё compliance.

Consequences: Writer РїРѕР»СѓС‡Р°РµС‚ СЃС‚СЂСѓРєС‚СѓСЂРёСЂРѕРІР°РЅРЅС‹Р№ РєРѕРЅС‚РµРєСЃС‚, Р° РЅРµ РїСЂРёРЅРёРјР°РµС‚ СЃРёСЃС‚РµРјРЅС‹Рµ СЂРµС€РµРЅРёСЏ РІ РѕРґРёРЅРѕС‡РєСѓ.



## ADR-003 - Context Assembly over "everything-in-prompt"

Status: accepted

Context: РїСЂСЏРјРѕРµ РІРєР»СЋС‡РµРЅРёРµ РІСЃРµР№ РёСЃС‚РѕСЂРёРё/РёСЃС‚РѕС‡РЅРёРєРѕРІ РІ prompt СѓРІРµР»РёС‡РёРІР°РµС‚ С€СѓРј Рё СЂРёСЃРє drift.

Decision: Context Assembly С„РѕСЂРјРёСЂСѓРµС‚ РѕРіСЂР°РЅРёС‡РµРЅРЅС‹Р№ СѓРїСЂР°РІР»СЏРµРјС‹Р№ context package.

Consequences: РІС‹С€Рµ predictability, РЅРёР¶Рµ СЂРёСЃРє РЅРµРєРѕРЅС‚СЂРѕР»РёСЂСѓРµРјС‹С… СЃСЃС‹Р»РѕРє Рё С†РёС‚РёСЂРѕРІР°РЅРёСЏ.



## ADR-004 - Knowledge Base is an internal lens library, not a quote source

Status: accepted

Context: РІРЅСѓС‚СЂРµРЅРЅРёРµ РєРЅРёРіРё Рё РјР°С‚РµСЂРёР°Р»С‹ РЅРµ РґРѕР»Р¶РЅС‹ СЃС‚Р°РЅРѕРІРёС‚СЊСЃСЏ user-facing С†РёС‚Р°С‚РЅРёРєРѕРј.

Decision: KB РёСЃРїРѕР»СЊР·СѓРµС‚СЃСЏ РєР°Рє internal lens/practice metadata library.

Consequences: Writer РЅРµ С†РёС‚РёСЂСѓРµС‚ `РљРЈР—РќРР¦РЈ Р”РЈРҐРђ` РЅР°РїСЂСЏРјСѓСЋ РїРѕР»СЊР·РѕРІР°С‚РµР»СЋ.



## ADR-005 - Deterministic governance is authority; LLM enrichment is advisory

Status: accepted

Context: LLM РјРѕР¶РµС‚ РїСЂРµРґР»РѕР¶РёС‚СЊ РїРѕР»РµР·РЅС‹Рµ summaries/lenses, РЅРѕ РґРѕРїСѓСЃРєР°РµС‚ РЅРµСЃС‚Р°Р±РёР»СЊРЅРѕСЃС‚СЊ С„РѕСЂРјСѓР»РёСЂРѕРІРѕРє.

Decision: `chunk_type/allowed_use/safety_flags` РѕСЃС‚Р°СЋС‚СЃСЏ deterministic authority.

Consequences: enrichment РїРѕРІС‹С€Р°РµС‚ РєР°С‡РµСЃС‚РІРѕ retrieval-context, РЅРµ СЂР°Р·СЂСѓС€Р°СЏ safety contracts.



## ADR-006 - Raw history preserved; summaries are additive

Status: accepted

Context: РєРѕРјРїСЂРµСЃСЃРёСЏ РёСЃС‚РѕСЂРёРё Р±РµР· СЃРѕС…СЂР°РЅРµРЅРёСЏ raw turns СЃРЅРёР¶Р°РµС‚ РґРµР±Р°Рі Рё РґРѕРІРµСЂРёРµ Рє trace.

Decision: raw dialogue history СЃРѕС…СЂР°РЅСЏРµС‚СЃСЏ РїРѕР»РЅРѕСЃС‚СЊСЋ, summary-СЃР»РѕРё РґРѕР±Р°РІРѕС‡РЅС‹Рµ.

Consequences: РјРѕР¶РЅРѕ СѓР»СѓС‡С€Р°С‚СЊ summaries Р±РµР· РїРѕС‚РµСЂРё РїРµСЂРІРёС‡РЅС‹С… РґР°РЅРЅС‹С….



## ADR-007 - Turn LLM summary must be async with deterministic fallback

Status: accepted

Context: СЃРёРЅС…СЂРѕРЅРЅР°СЏ summary-РіРµРЅРµСЂР°С†РёСЏ РјРѕР¶РµС‚ Р±Р»РѕРєРёСЂРѕРІР°С‚СЊ response path Рё РґРµРіСЂР°РґРёСЂРѕРІР°С‚СЊ UX.

Decision: async per-turn summary СЂРµР°Р»РёР·СѓРµС‚СЃСЏ РєР°Рє additive СЃР»РѕР№ (`pending|ready|failed`) Рё РёСЃРїРѕР»СЊР·СѓРµС‚СЃСЏ РІ context assembly С‚РѕР»СЊРєРѕ РїСЂРё `ready+valid+hash-match`; РёРЅР°С‡Рµ deterministic fallback.

Consequences: semantic continuity СѓР»СѓС‡С€Р°РµС‚СЃСЏ Р±РµР· Р±Р»РѕРєРёСЂРѕРІРєРё user-response path Рё Р±РµР· СЂРёСЃРєР° РїРѕС‚РµСЂРё РєРѕРЅС‚РµРєСЃС‚Р° РїСЂРё СЃР±РѕСЏС… LLM/provider.



## ADR-008 - Diagnostic Center deferred until readiness gates pass

Status: accepted

Context: РїСЂРµР¶РґРµРІСЂРµРјРµРЅРЅС‹Р№ Р·Р°РїСѓСЃРє Diagnostic Center РїСЂРё РЅРµРіРѕС‚РѕРІРѕРј KB/context РґР°СЃС‚ Р»РѕР¶РЅСѓСЋ СѓРІРµСЂРµРЅРЅРѕСЃС‚СЊ.

Decision: Р·Р°РїСѓСЃРє С‚РѕР»СЊРєРѕ РїРѕСЃР»Рµ APPLY1, retrieval eval Рё context-quality РїСЂРѕРіСЂРµСЃСЃР°.

Consequences: Р±РѕР»РµРµ РЅР°РґРµР¶РЅС‹Р№ Рё РёРЅС‚РµСЂРїСЂРµС‚РёСЂСѓРµРјС‹Р№ РґРёР°РіРЅРѕСЃС‚РёС‡РµСЃРєРёР№ СЃР»РѕР№.



## ADR-009 - Applied enrichment stored as advisory metadata only

Status: accepted

Context: РїРѕСЃР»Рµ real LLM calibration РїРѕСЏРІРёР»СЃСЏ production-candidate overlay, РЅРѕ governance authority РґРѕР»Р¶РЅР° РѕСЃС‚Р°РІР°С‚СЊСЃСЏ deterministic.

Decision: APPLY1 Р·Р°РїРёСЃС‹РІР°РµС‚ enrichment С‚РѕР»СЊРєРѕ РІ `metadata.llm_enrichment` Рё retrieval metadata pass-through, РЅРµ РјРµРЅСЏСЏ `text/chunk_type/allowed_use/safety_flags`.

Consequences: РјРѕР¶РЅРѕ РёСЃРїРѕР»СЊР·РѕРІР°С‚СЊ enrichment РґР»СЏ РєРѕРЅС‚РµРєСЃС‚РЅРѕРіРѕ СѓР»СѓС‡С€РµРЅРёСЏ retrieval Р±РµР· РїРѕРґРјРµРЅС‹ safety/governance РєРѕРЅС‚СЂР°РєС‚РѕРІ.



## ADR-010 - Turn summary validator must include safety-content guards

Status: accepted

Context: Р±Р°Р·РѕРІР°СЏ РїСЂРѕРІРµСЂРєР° `ready/hash/version` РЅРµРґРѕСЃС‚Р°С‚РѕС‡РЅР° РґР»СЏ Р±РµР·РѕРїР°СЃРЅРѕРіРѕ РёСЃРїРѕР»СЊР·РѕРІР°РЅРёСЏ summary РІ context assembly.

Decision: validator РґР»СЏ turn summaries РѕР±СЏР·Р°РЅ РѕС‚РєР»РѕРЅСЏС‚СЊ diagnosis assertions, direct advice/action voice, transcript-style dumps Рё overlong quote/summary payloads.

Consequences: unsafe summaries Р°РІС‚РѕРјР°С‚РёС‡РµСЃРєРё СѓС…РѕРґСЏС‚ РІ deterministic fallback, Р° РєРѕРЅС‚РµРєСЃС‚РЅС‹Р№ СЃР»РѕР№ РѕСЃС‚Р°С‘С‚СЃСЏ СѓСЃС‚РѕР№С‡РёРІС‹Рј РїРµСЂРµРґ Р·Р°РїСѓСЃРєРѕРј retrieval-eval С†РёРєР»Р°.



## ADR-011 - Retrieval eval gate is mandatory before Diagnostic Center/Admin Review scale-up

Status: accepted

Context: РїРѕСЃР»Рµ APPLY1 РєР°С‡РµСЃС‚РІРѕ retrieval РґРѕР»Р¶РЅРѕ РїРѕРґС‚РІРµСЂР¶РґР°С‚СЊСЃСЏ РІРѕСЃРїСЂРѕРёР·РІРѕРґРёРјРѕ, РёРЅР°С‡Рµ downstream diagnostic/review workflows Р±СѓРґСѓС‚ РѕРїРёСЂР°С‚СЊСЃСЏ РЅР° СЃР»СѓС‡Р°Р№РЅС‹Р№ РєРѕРЅС‚РµРєСЃС‚.

Decision: РїРµСЂРµРґ СЂР°СЃС€РёСЂРµРЅРёРµРј РІ `PRD-046.0.7` РѕР±СЏР·Р°С‚РµР»РµРЅ deterministic retrieval eval gate (dataset + runner + scorecard + weak-case queue) Рё Р·Р°РєСЂС‹С‚РёРµ safety-gap РїРѕ `internal_only` exposure.

Consequences: Р·Р°РїСѓСЃРє Admin Review/Diagnostic Center РѕС‚РєР»Р°РґС‹РІР°РµС‚СЃСЏ РґРѕ Р·Р°РєСЂС‹С‚РёСЏ `PRD-046.0.6-HF1`, РґР°Р¶Рµ РїСЂРё С…РѕСЂРѕС€РµРј semantic/gov coverage.



## ADR-012 - Internal-only retrieval hits are suppressed for non-safety user contexts

Status: accepted

Context: PRD-046.0.6 РїРѕРєР°Р·Р°Р» СѓС‚РµС‡РєСѓ `internal_only` hits РІ non-safety top-k РїСЂРё СЃРѕС…СЂР°РЅРµРЅРёРё С…РѕСЂРѕС€РµРіРѕ semantic РєР°С‡РµСЃС‚РІР°.

Decision: API-side retrieval policy (`retrieval_governance_safety_v1`) РёСЃРєР»СЋС‡Р°РµС‚ `internal_only` hits РёР· С„РёРЅР°Р»СЊРЅРѕРіРѕ top-k РґР»СЏ non-safety Р·Р°РїСЂРѕСЃРѕРІ; РґР»СЏ safety-context allowance СЃРѕС…СЂР°РЅСЏРµС‚СЃСЏ.

Consequences: Р·Р°РєСЂС‹С‚ safety-gate (`internal_only_unsafe_exposure_count=0`) Р±РµР· РѕСЃР»Р°Р±Р»РµРЅРёСЏ dataset Рё Р±РµР· РјСѓС‚Р°С†РёРё KB/governance authority.



## ADR-013 - Human review decisions are stored as separate overlays before any KB apply step

Status: accepted

Context: РїРѕСЃР»Рµ APPLY1 enrichment advisory metadata С‚СЂРµР±СѓРµС‚ human-review, РЅРѕ РїСЂСЏРјРѕРµ РїСЂРёРјРµРЅРµРЅРёРµ review СЂРµС€РµРЅРёР№ РІ production KB Р±РµР· РѕС‚РґРµР»СЊРЅРѕРіРѕ controlled apply С€Р°РіР° РїРѕРІС‹С€Р°РµС‚ СЂРёСЃРє governance drift Рё РЅРµР°СѓРґРёСЂСѓРµРјС‹С… РјСѓС‚Р°С†РёР№.

Decision: workflow `PRD-046.0.7` РѕРіСЂР°РЅРёС‡РёРІР°РµС‚СЃСЏ Р±РµР·РѕРїР°СЃРЅС‹Рј СЃР±РѕСЂРѕРј review queue Рё РІР°Р»РёРґР°С†РёРµР№ decisions overlay; СЂРµС€РµРЅРёСЏ С…СЂР°РЅСЏС‚СЃСЏ РѕС‚РґРµР»СЊРЅРѕ Рё РЅРµ РїСЂРёРјРµРЅСЏСЋС‚СЃСЏ Рє `all_blocks_merged.json`/Chroma РІ СЂР°РјРєР°С… СЌС‚РѕРіРѕ С†РёРєР»Р°.

Consequences: review РїСЂРѕС†РµСЃСЃ СЃС‚Р°РЅРѕРІРёС‚СЃСЏ РІРѕСЃРїСЂРѕРёР·РІРѕРґРёРјС‹Рј Рё РїСЂРѕРІРµСЂСЏРµРјС‹Рј (sanitized artifacts + no-mutation proof), Р° С„Р°РєС‚РёС‡РµСЃРєРёР№ apply РїРµСЂРµРЅРѕСЃРёС‚СЃСЏ РІ РѕС‚РґРµР»СЊРЅС‹Р№ PRD СЃ preflight/dry-run safety gates.



## ADR-014 - Legacy SD classification is decommissioned from active BotDB admin/query path

Status: accepted

Context: SD-РїРѕР»СЏ РёСЃС‚РѕСЂРёС‡РµСЃРєРё РїСЂРёСЃСѓС‚СЃС‚РІСѓСЋС‚ РІ РґР°РЅРЅС‹С…, РЅРѕ РёС… Р°РєС‚РёРІРЅРѕРµ РёСЃРїРѕР»СЊР·РѕРІР°РЅРёРµ РІ BotDB Admin/UI/API РєР°Рє production-СЃРёРіРЅР°Р»Р° СЃРѕР·РґР°С‘С‚ Р»РѕР¶РЅСѓСЋ РјРѕРґРµР»СЊ СЃРѕСЃС‚РѕСЏРЅРёСЏ KB Рё РјРµС€Р°РµС‚ hygiene/reprocess readiness СЌС‚Р°РїСѓ.

Decision: РґР»СЏ BotDB admin/query surfaces SD Р±РѕР»СЊС€Рµ РЅРµ РёСЃРїРѕР»СЊР·СѓРµС‚СЃСЏ РєР°Рє active filter/signal; РІ `/api/query` `sd_level` РїРµСЂРµРІРѕРґРёС‚СЃСЏ РІ deprecated no-op СЃ СЏРІРЅС‹Рј debug trace, Р° SD-РІРёР·СѓР°Р»С‹ СѓРґР°Р»СЏСЋС‚СЃСЏ РёР· dashboard/registry UI.

Consequences: СЃРЅРёР¶РµРЅ СЂРёСЃРє РѕС€РёР±РѕС‡РЅРѕРіРѕ operational СЂРµС€РµРЅРёСЏ РЅР° SD-СЃРёРіРЅР°Р»Р°С…; СЃРѕРІРјРµСЃС‚РёРјРѕСЃС‚СЊ РєР»РёРµРЅС‚РѕРІ СЃРѕС…СЂР°РЅРµРЅР° С‡РµСЂРµР· backward-compatible РїРѕР»Рµ Р±РµР· РІР»РёСЏРЅРёСЏ РЅР° retrieval.



## ADR-015 - Source registry cleanup must go through snapshot+archive workflow before clean reprocess

Status: accepted

Context: СЂСѓС‡РЅС‹Рµ СѓРґР°Р»РµРЅРёСЏ Рё СЃРјРµС€Р°РЅРЅС‹Рµ test/stale РёСЃС‚РѕС‡РЅРёРєРё РІ registry РїСЂРёРІРѕРґСЏС‚ Рє РЅРµРїСЂРѕР·СЂР°С‡РЅРѕРјСѓ СЃРѕСЃС‚РѕСЏРЅРёСЋ Рё Р±Р»РѕРєРёСЂСѓСЋС‚ Р±РµР·РѕРїР°СЃРЅС‹Р№ clean reprocess.

Decision: cleanup РІС‹РїРѕР»РЅСЏРµС‚СЃСЏ С‡РµСЂРµР· РєРѕРЅС‚СЂРѕР»РёСЂСѓРµРјС‹Р№ `audit -> plan -> dry-run/apply` РїСЂРѕС†РµСЃСЃ СЃ РѕР±СЏР·Р°С‚РµР»СЊРЅРѕР№ Р·Р°С‰РёС‚РѕР№ focus source Рё Р·Р°РїСЂРµС‚РѕРј hard-delete РёСЃС‚РѕС‡РЅРёРєРѕРІ СЃ `blocks_count > 0`; РїРµСЂРµРґ mutation РѕР±СЏР·Р°С‚РµР»РµРЅ snapshot.

Consequences: СѓР»СѓС‡С€РµРЅР° РІРѕСЃРїСЂРѕРёР·РІРѕРґРёРјРѕСЃС‚СЊ Рё РѕР±СЂР°С‚РёРјРѕСЃС‚СЊ hygiene-РѕРїРµСЂР°С†РёР№; readiness gate РјРѕР¶РµС‚ РґРµС‚РµСЂРјРёРЅРёСЂРѕРІР°РЅРЅРѕ РѕР±СЉСЏСЃРЅСЏС‚СЊ blockers/warnings РїРµСЂРµРґ Р·Р°РїСѓСЃРєРѕРј reprocess.



## ADR-016 - Clean source reprocess must be candidate-first before any production apply/reindex

Status: accepted

Context: РїРѕСЃР»Рµ Р·Р°РєСЂС‹С‚РёСЏ hygiene blocker РЅСѓР¶РЅРѕ РїРµСЂРµСЃРѕР±СЂР°С‚СЊ knowledge source РёР· raw markdown, РЅРѕ РїСЂСЏРјРѕР№ apply РІ production (`all_blocks_merged`/Chroma/registry) Р±РµР· РёР·РјРµСЂРёРјРѕРіРѕ candidate quality СѓРІРµР»РёС‡РёРІР°РµС‚ СЂРёСЃРє regression Рё РЅРµ РґР°С‘С‚ РёР·РѕР»РёСЂРѕРІР°С‚СЊ РїСЂРёС‡РёРЅСѓ РґРµРіСЂР°РґР°С†РёРё.

Decision: СЌС‚Р°Рї `PRD-046.0.8` РІС‹РїРѕР»РЅСЏРµС‚СЃСЏ С‚РѕР»СЊРєРѕ РІ `candidate` СЂРµР¶РёРјРµ: reprocess СЃС‚СЂРѕРёС‚СЃСЏ РёР· single active source, С„РѕСЂРјРёСЂСѓСЋС‚СЃСЏ preflight/stats/diff/governance gate/practice-like/no-mutation Р°СЂС‚РµС„Р°РєС‚С‹, РїСЂРё СЌС‚РѕРј production data Рё runtime path РЅРµ РјСѓС‚РёСЂСѓСЋС‚СЃСЏ.

Consequences: СЂРµС€РµРЅРёРµ Рѕ reindex/apply РїРµСЂРµРЅРѕСЃРёС‚СЃСЏ РІ РѕС‚РґРµР»СЊРЅС‹Р№ PRD РЅР° РѕСЃРЅРѕРІРµ gate-СЂРµР·СѓР»СЊС‚Р°С‚Р°; РїСЂРё РїСЂРѕР±Р»РµРјР°С… РєР»Р°СЃСЃРёС„РёРєР°С†РёРё Р·Р°РїСѓСЃРєР°РµС‚СЃСЏ HF-РєР°Р»РёР±СЂРѕРІРєР° РІРјРµСЃС‚Рѕ РѕРїР°СЃРЅРѕР№ production РјСѓС‚Р°С†РёРё.



## ADR-017 - Direct practice protocols require deterministic classification before candidate apply

Status: accepted

Context: РїРѕСЃР»Рµ `PRD-046.0.8` candidate РїРѕРєР°Р·Р°Р» practice-like ambiguity (`practice_like_misclassified_count > 0`), С‡С‚Рѕ РґРµР»Р°Р»Рѕ РїРµСЂРµС…РѕРґ Рє controlled apply/reindex СЂРёСЃРєРѕРІР°РЅРЅС‹Рј.

Decision: РґР»СЏ candidate-governance РІРІРѕРґРёС‚СЃСЏ deterministic practice taxonomy (`direct_practice_protocol`, `practice_context_or_theory`, `case_or_dialogue_about_practice`, `quote_or_source_fragment_with_practice_terms`) Рё gate v2 СЃ РѕС‚РґРµР»СЊРЅС‹РјРё РјРµС‚СЂРёРєР°РјРё `direct_practice_misclassified_count` Рё `unsafe_practice_suggestion_count`. Direct practice РѕР±СЏР·Р°РЅ РёРјРµС‚СЊ `chunk_type=practice`, `practice_suggestion` РІ `allowed_use`, Р° С‚Р°РєР¶Рµ safety bundle (`not_for_direct_quote`, `practice_requires_low_resource_check`).

Consequences: candidate apply/reindex Р·Р°РїСЂРµС‰РµРЅ, РїРѕРєР° direct-practice misclassification РЅРµ СЂР°РІРµРЅ `0`; contextual/mixed-intent warnings РѕР±СЂР°Р±Р°С‚С‹РІР°СЋС‚СЃСЏ РѕС‚РґРµР»СЊРЅС‹Рј HF-warning С†РёРєР»РѕРј Р±РµР· РјСѓС‚Р°С†РёРё production РґР°РЅРЅС‹С….



## ADR-018 - Mixed-intent candidate chunks must be resolved before production apply

Status: accepted

Context: РїРѕСЃР»Рµ `PRD-046.0.8-HF1` РѕСЃС‚Р°РІР°Р»РёСЃСЊ mixed-intent high/medium warnings, С‡С‚Рѕ СЃРѕС…СЂР°РЅСЏР»Рѕ СЂРёСЃРє РЅРµРѕС‡РµРІРёРґРЅРѕРіРѕ governance-РїРѕРІРµРґРµРЅРёСЏ РїСЂРё РїРµСЂРµС…РѕРґРµ Рє apply/reindex.

Decision: РІРІРѕРґРёС‚СЃСЏ candidate mixed-intent audit+resolution taxonomy (`split_required`, `primary_role_resolved`, `review_only`, `false_positive`) Рё gate v3 СЃ РїРѕР»СЏРјРё `mixed_intent_unresolved_count`, `mixed_intent_split_required_count`, `candidate_ready_for_apply`. Production apply/reindex СЂР°Р·СЂРµС€Р°РµС‚СЃСЏ С‚РѕР»СЊРєРѕ РїСЂРё `status=passed` Рё `candidate_ready_for_apply=true`.

Consequences: unresolved/split-required mixed-intent РєРµР№СЃС‹ Р±Р»РѕРєРёСЂСѓСЋС‚ apply; false-positive Рё review-only СЃС†РµРЅР°СЂРёРё РѕСЃС‚Р°СЋС‚СЃСЏ РїСЂРѕР·СЂР°С‡РЅС‹РјРё С‡РµСЂРµР· candidate metadata Р±РµР· РјСѓС‚Р°С†РёРё production РєРѕРЅС‚СѓСЂРѕРІ.



## ADR-019 - Candidate apply to production requires preflight, backups, controlled reindex, and post-apply retrieval gates

Status: accepted

Context: РїРµСЂРµС…РѕРґ candidate (`PRD-046.0.8-HF2`) РІ production РЅРµСЃРµС‚ РІС‹СЃРѕРєРёР№ СЂРёСЃРє РЅРµСЃРѕРіР»Р°СЃРѕРІР°РЅРЅРѕСЃС‚Рё РјРµР¶РґСѓ `all_blocks_merged`, registry Рё Chroma, Р° С‚Р°РєР¶Рµ СЂРёСЃРє РЅРµРєРѕСЂСЂРµРєС‚РЅРѕРіРѕ РїРѕРІС‚РѕСЂРЅРѕРіРѕ РёСЃРїРѕР»СЊР·РѕРІР°РЅРёСЏ СѓСЃС‚Р°СЂРµРІС€РёС… review artifacts.

Decision: apply СЂР°Р·СЂРµС€Р°РµС‚СЃСЏ С‚РѕР»СЊРєРѕ С‡РµСЂРµР· staged workflow: `preflight -> dry-run apply plan -> mandatory backups -> controlled production mutation -> Chroma reindex/recovery -> post-apply consistency/quality/retrieval gates`.

Consequences: production KB СЃС‚Р°РЅРѕРІРёС‚СЃСЏ Р°СѓРґРёСЂСѓРµРјС‹Рј Рё РІРѕСЃРїСЂРѕРёР·РІРѕРґРёРјС‹Рј РїРѕСЃР»Рµ reprocess; СЃС‚Р°СЂС‹Рµ review queues РїРѕРјРµС‡Р°СЋС‚СЃСЏ stale, Р° РґР°Р»СЊРЅРµР№С€РёР№ review/apply С†РёРєР» РґРѕР»Р¶РµРЅ РѕРїРёСЂР°С‚СЊСЃСЏ РЅР° РЅРѕРІС‹Рµ block ids.



## ADR-020 - Post-reprocess enrichment and review must be regenerated against current block ids

Status: accepted

Context: РїРѕСЃР»Рµ boundary-changing reprocess (`PRD-046.0.8.1`) СЃС‚Р°СЂС‹Рµ enrichment/review Р°СЂС‚РµС„Р°РєС‚С‹ СЃС‚Р°Р»Рё СЃРµРјР°РЅС‚РёС‡РµСЃРєРё Рё С‚РµС…РЅРёС‡РµСЃРєРё stale, РґР°Р¶Рµ РїСЂРё С‡Р°СЃС‚РёС‡РЅРѕРј С‚РµРјР°С‚РёС‡РµСЃРєРѕРј СЃРѕРІРїР°РґРµРЅРёРё С‚РµРєСЃС‚Р°.

Decision: РґР»СЏ post-reprocess СЌС‚Р°РїР° РѕР±СЏР·Р°С‚РµР»РµРЅ fresh baseline (`PRD-046.0.9`) СЃ preflight, inventory, overlay validation Рё review queue rebaseline, РїСЂРёРІСЏР·Р°РЅРЅС‹РјРё Рє С‚РµРєСѓС‰РёРј block ids/hash. РЎС‚Р°СЂС‹Рµ СЂРµС€РµРЅРёСЏ РЅРµ РїСЂРёРјРµРЅСЏСЋС‚СЃСЏ Р±РµР· СЏРІРЅРѕРіРѕ remap+hash proof.

Consequences: review/apply С†РёРєР» РѕСЃС‚Р°РµС‚СЃСЏ С‚СЂР°СЃСЃРёСЂСѓРµРјС‹Рј Рё Р±РµР·РѕРїР°СЃРЅС‹Рј; РёСЃРєР»СЋС‡Р°РµС‚СЃСЏ silent РїРµСЂРµРЅРѕСЃ СЃС‚Р°СЂС‹С… СЂРµС€РµРЅРёР№ РЅР° РЅРѕРІС‹Рµ РіСЂР°РЅРёС†С‹ С‡Р°РЅРєРѕРІ; LLM enrichment СЃРѕС…СЂР°РЅСЏРµС‚ advisory СЂРѕР»СЊ Рё РЅРµ РјРѕР¶РµС‚ РјСѓС‚РёСЂРѕРІР°С‚СЊ deterministic governance authority.



## ADR-021 - BotDB Admin Dashboard must use explicit read-only summary contract

Status: accepted

Context: РїРѕСЃР»Рµ `PRD-046.0.9-RUN1` registry РѕС‚СЂР°Р¶Р°Р» Р°РєС‚СѓР°Р»СЊРЅС‹Рµ РґР°РЅРЅС‹Рµ, РЅРѕ dashboard РїРѕРєР°Р·С‹РІР°Р» РїСѓСЃС‚С‹Рµ РєР°СЂС‚РѕС‡РєРё РёР·-Р·Р° С…СЂСѓРїРєРѕР№ СЃР±РѕСЂРєРё СЃРѕСЃС‚РѕСЏРЅРёСЏ РёР· СЂР°Р·СЂРѕР·РЅРµРЅРЅС‹С… РІС‹Р·РѕРІРѕРІ Рё РѕС‚СЃСѓС‚СЃС‚РІРёСЏ СЏРІРЅРѕР№ РґРµРіСЂР°РґР°С†РёРё РїСЂРё РїСЂРѕР±Р»РµРјР°С… РёСЃС‚РѕС‡РЅРёРєРѕРІ РґР°РЅРЅС‹С….

Decision: dashboard РїРµСЂРµРІРѕРґРёС‚СЃСЏ РЅР° РµРґРёРЅС‹Р№ read-only РєРѕРЅС‚СЂР°РєС‚ `/api/dashboard/` (`botdb_dashboard_summary_v1`), РєРѕС‚РѕСЂС‹Р№ Р°РіСЂРµРіРёСЂСѓРµС‚ registry/chroma/governance/enrichment/review state Рё РІРѕР·РІСЂР°С‰Р°РµС‚ СЏРІРЅС‹Рµ `warnings` РїСЂРё С‡Р°СЃС‚РёС‡РЅРѕР№ РЅРµРґРѕСЃС‚СѓРїРЅРѕСЃС‚Рё Р°СЂС‚РµС„Р°РєС‚РѕРІ.

Consequences: admin UI РѕС‚РѕР±СЂР°Р¶Р°РµС‚ РґРѕСЃС‚РѕРІРµСЂРЅРѕРµ РѕРїРµСЂР°С†РёРѕРЅРЅРѕРµ СЃРѕСЃС‚РѕСЏРЅРёРµ, РЅРµ РјСѓС‚РёСЂСѓРµС‚ production РґР°РЅРЅС‹Рµ Рё РЅРµ РјР°СЃРєРёСЂСѓРµС‚ РѕС€РёР±РєРё РЅРµРјС‹РјРё `вЂ”` РєР°СЂС‚РѕС‡РєР°РјРё.



## ADR-022 - Admin UI acceptance requires runtime/browser-visible smoke, not only TestClient

Status: accepted

Context: РїРѕСЃР»Рµ HF1 API unit tests Р±С‹Р»Рё Р·РµР»С‘РЅС‹РјРё, РЅРѕ СЂСѓС‡РЅР°СЏ РїСЂРѕРІРµСЂРєР° Р±СЂР°СѓР·РµСЂРЅРѕРіРѕ runtime РІСЃС‘ РµС‰С‘ РїРѕРєР°Р·С‹РІР°Р»Р° СѓСЃС‚Р°СЂРµРІС€РёР№/РїСѓСЃС‚РѕР№ dashboard UI.

Decision: РґР»СЏ Admin UI hotfix-С†РёРєР»РѕРІ РѕР±СЏР·Р°С‚РµР»СЊРЅС‹ runtime-oriented smoke checks: СЃС‚Р°С‚РёС‡РµСЃРєРёР№ contract (HTML script version, JS fetch path), endpoint slash/no-slash compatibility Рё СЏРІРЅС‹Р№ UI fallback РЅР° API/payload РѕС€РёР±РєРё.

Consequences: acceptance РЅРµ Р·Р°РІРµСЂС€Р°РµС‚СЃСЏ С‚РѕР»СЊРєРѕ TestClient-СѓСЂРѕРІРЅРµРј; PRD СЃС‡РёС‚Р°РµС‚СЃСЏ Р·Р°РєСЂС‹С‚С‹Рј РїРѕСЃР»Рµ РїРѕРґС‚РІРµСЂР¶РґРµРЅРёСЏ browser-visible РєРѕРЅС‚СЂР°РєС‚Р°.



## ADR-023 - Writer KB snippets must be boundary-aware and never cut Cyrillic words mid-token

Status: accepted

Context: РІ runtime prompt `Р—РќРђРќРРЇ РР— Р‘РђР—Р«` С„РёРєСЃРёСЂРѕРІР°Р»РёСЃСЊ РѕР±СЂРµР·Р°РЅРЅС‹Рµ С„СЂР°РіРјРµРЅС‚С‹ (`Р”РѕР±СЂРѕ РїРѕР¶Р°Р»РѕРІР°С‚`, `Р•С€СЊ РЅР° Р±Рµ`), СѓС…СѓРґС€Р°СЋС‰РёРµ РєР°С‡РµСЃС‚РІРѕ РєРѕРЅС‚РµРєСЃС‚Р° РґР»СЏ Writer.

Decision: sanitization/truncation РґР»СЏ writer-facing KB snippets РґРѕР»Р¶РЅР° СЂРµР·Р°С‚СЊ РїРѕ sentence/word boundary Рё РґРѕР±Р°РІР»СЏС‚СЊ ellipsis `вЂ¦`, Р° РЅРµ РёСЃРїРѕР»СЊР·РѕРІР°С‚СЊ raw fixed-char clipping.

Consequences: СЃРЅРёР¶Р°РµС‚СЃСЏ С€СѓРј Рё РґРІСѓСЃРјС‹СЃР»РµРЅРЅРѕСЃС‚СЊ РІ writer prompt РїСЂРё СЃРѕС…СЂР°РЅРµРЅРёРё budget limits Рё Р±РµР· РјСѓС‚Р°С†РёРё production block text.



## ADR-024 - Admin source registry must be row-isolated and never fail silently

Status: accepted

Context: РїСЂРё runtime-РїСЂРѕРІРµСЂРєРµ РїРѕСЃР»Рµ HF2 registry page РјРѕРіР»Р° РѕС‚РєСЂС‹РІР°С‚СЊСЃСЏ СЃ РїСѓСЃС‚РѕР№ С‚Р°Р±Р»РёС†РµР№, С…РѕС‚СЏ РёСЃС‚РѕС‡РЅРёРєРё РІ СЃРёСЃС‚РµРјРµ Р±С‹Р»Рё; РѕРґРёРЅ РїСЂРѕР±Р»РµРјРЅС‹Р№ row/policy path РїРѕС‚РµРЅС†РёР°Р»СЊРЅРѕ СЂРѕРЅСЏР» РІРµСЃСЊ payload, Р° frontend РЅРµ РїРѕРєР°Р·С‹РІР°Р» СЏРІРЅС‹Р№ error state.

Decision: endpoint `/api/registry/` РѕР±СЏР·Р°РЅ РѕР±СЂР°Р±Р°С‚С‹РІР°С‚СЊ РѕС€РёР±РєРё РЅР° СѓСЂРѕРІРЅРµ СЃС‚СЂРѕРєРё (row-level isolation), РІРѕР·РІСЂР°С‰Р°С‚СЊ С‡Р°СЃС‚РёС‡РЅС‹Р№ СЃРїРёСЃРѕРє СЃ `delete_policy.state=unavailable` Рё РїСЂРёС‡РёРЅР°РјРё, Р° frontend РѕР±СЏР·Р°РЅ РёРјРµС‚СЊ СЏРІРЅС‹Рµ loading/error/empty states РІРјРµСЃС‚Рѕ silent empty table.

Consequences: РѕС‚РєР°Р· РѕРґРЅРѕР№ СЃС‚СЂРѕРєРё Р±РѕР»СЊС€Рµ РЅРµ Р±Р»РѕРєРёСЂСѓРµС‚ РІРµСЃСЊ admin registry, Р° browser-visible РґРёР°РіРЅРѕСЃС‚РёРєР° РґРµР»Р°РµС‚ runtime РїСЂРѕР±Р»РµРјС‹ РІРѕСЃРїСЂРѕРёР·РІРѕРґРёРјС‹РјРё Рё РїСЂРѕРІРµСЂСЏРµРјС‹РјРё РґРѕ РїРµСЂРµС…РѕРґР° Рє human-review С†РёРєР»Р°Рј.



## ADR-025 - Admin/API runtime gate cannot pass when required endpoints are unreachable

Status: accepted

Context: РїРѕСЃР»Рµ controlled apply data-level РїСЂРѕРІРµСЂРєРё РјРѕРіР»Рё Р±С‹С‚СЊ Р·РµР»С‘РЅС‹РјРё РґР°Р¶Рµ РїСЂРё `connection refused` РЅР° admin endpoints, С‡С‚Рѕ СЃРѕР·РґР°РІР°Р»Рѕ Р»РѕР¶РЅС‹Р№ signal РіРѕС‚РѕРІРЅРѕСЃС‚Рё РїРµСЂРµРґ СЃР»РµРґСѓСЋС‰РёРј Р°СЂС…РёС‚РµРєС‚СѓСЂРЅС‹Рј СЌС‚Р°РїРѕРј.

Decision: post-apply quality gate РѕР±СЏР·Р°РЅ СЂР°Р·РґРµР»СЏС‚СЊ data consistency Рё admin runtime consistency; РїСЂРё РЅРµРґРѕСЃС‚СѓРїРЅРѕСЃС‚Рё `/api/status`, `/api/registry`, `/api/dashboard`, `/api/dashboard/` СЃС‚Р°С‚СѓСЃ РґРѕР»Р¶РµРЅ Р±С‹С‚СЊ `blocked_admin_api_unavailable` (РёР»Рё `skipped_offline_explicit` РїСЂРё СЏРІРЅРѕРј offline-СЂРµР¶РёРјРµ), РЅРѕ РЅРµ `passed`.

Consequences: readiness Рє Diagnostic Center РЅРµ РјРѕР¶РµС‚ СЃС‚Р°С‚СЊ `true` Р±РµР· РїРѕРґС‚РІРµСЂР¶РґС‘РЅРЅРѕР№ РґРѕСЃС‚СѓРїРЅРѕСЃС‚Рё admin/API runtime, Р° РѕС‚С‡С‘С‚С‹ РєРѕСЂСЂРµРєС‚РЅРѕ РѕС‚СЂР°Р¶Р°СЋС‚ blocker РІРјРµСЃС‚Рѕ Р»РѕР¶РЅРѕРіРѕ green.



## ADR-026 - Live admin runtime smoke uses dual launch mode with readiness polling

Status: accepted

Context: РґР»СЏ post-apply readiness gate С‚СЂРµР±СѓРµС‚СЃСЏ РїСЂРѕРІРµСЂСЏС‚СЊ СЂРµР°Р»СЊРЅС‹Р№ runtime admin endpoints; РїСЂРё СЌС‚РѕРј СЃРµСЂРІРµСЂ РјРѕР¶РµС‚ Р±С‹С‚СЊ СѓР¶Рµ Р·Р°РїСѓС‰РµРЅ РїРѕР»СЊР·РѕРІР°С‚РµР»РµРј РёР»Рё РґРѕР»Р¶РµРЅ РїРѕРґРЅРёРјР°С‚СЊСЃСЏ РІСЂРµРјРµРЅРЅРѕ Р°РіРµРЅС‚РѕРј.

Decision: HF1 live smoke РёСЃРїРѕР»СЊР·СѓРµС‚ dual strategy: `external_existing` (РЅРµ Р·Р°РїСѓСЃРєР°С‚СЊ РІС‚РѕСЂРѕР№ СЃРµСЂРІРµСЂ РЅР° С‚РѕРј Р¶Рµ РїРѕСЂС‚Сѓ) Рё `hf1_subprocess` (detected canonical launch command + startup polling + controlled shutdown). Р•СЃР»Рё readiness РЅРµ РґРѕСЃС‚РёРіРЅСѓС‚ РёР»Рё Р·Р°РїСѓСЃРє РЅРµРІРѕР·РјРѕР¶РµРЅ, СЃС‚Р°С‚СѓСЃ РѕР±СЏР·Р°РЅ РѕСЃС‚Р°РІР°С‚СЊСЃСЏ blocker (`blocked_admin_launch_failed`), Р±РµР· Р»РѕР¶РЅРѕРіРѕ green.

Consequences: gate СЃС‚Р°РЅРѕРІРёС‚СЃСЏ РІРѕСЃРїСЂРѕРёР·РІРѕРґРёРјС‹Рј Рё С‚СЂР°СЃСЃРёСЂСѓРµРјС‹Рј (manifest + sanitized logs + explicit blocker reason) Р±РµР· РјСѓС‚Р°С†РёРё production РґР°РЅРЅС‹С….



## ADR-027 - Admin gate may accept dashboard Chroma mismatch only with explicit local proof

Status: superseded_by_adr_028

Context: РІ HF2 live runtime dashboard РјРѕРі РІРѕР·РІСЂР°С‰Р°С‚СЊ `chroma.count`, РѕС‚Р»РёС‡Р°СЋС‰РёР№СЃСЏ РѕС‚ РѕР¶РёРґР°РµРјРѕРіРѕ production count, С…РѕС‚СЏ РѕС‚РґРµР»СЊРЅР°СЏ Р»РѕРєР°Р»СЊРЅР°СЏ Chroma diagnostics-РїСЂРѕРІРµСЂРєР° РїРѕРґС‚РІРµСЂР¶РґР°Р»Р° РєРѕСЂСЂРµРєС‚РЅС‹Р№ `247` РґР»СЏ focus source.

Decision: quality gate РЅРµ Р±Р»РѕРєРёСЂСѓРµС‚СЃСЏ С‚РѕР»СЊРєРѕ РїСЂРё РЅР°Р»РёС‡РёРё СЏРІРЅРѕРіРѕ Р»РѕРєР°Р»СЊРЅРѕРіРѕ proof-Р°СЂС‚РµС„Р°РєС‚Р° СЃ РѕР¶РёРґР°РµРјС‹Рј count; mismatch Р±РµР· proof РѕСЃС‚Р°С‘С‚СЃСЏ schema blocker. РџСЂРёРЅСЏС‚РёРµ mismatch РІСЃРµРіРґР° С„РёРєСЃРёСЂСѓРµС‚СЃСЏ РїСЂРµРґСѓРїСЂРµР¶РґРµРЅРёРµРј РІ artifacts/reports.

Consequences: СЃРѕС…СЂР°РЅСЏРµС‚СЃСЏ СЃС‚СЂРѕРіРёР№ gate РїРѕ СѓРјРѕР»С‡Р°РЅРёСЋ, РЅРѕ РёСЃРєР»СЋС‡Р°РµС‚СЃСЏ Р»РѕР¶РЅС‹Р№ blocker РїСЂРё СЃРѕРІРјРµСЃС‚РёРјРѕРј runtime contract drift Рё РїРѕРґС‚РІРµСЂР¶РґРµРЅРЅРѕР№ Р»РѕРєР°Р»СЊРЅРѕР№ РґРёР°РіРЅРѕСЃС‚РёРєРµ.



## ADR-028 - Historical Chroma proof cannot override live dashboard mismatch in strict gate

Status: accepted

Context: HF3 РїРѕРєР°Р·Р°Р», С‡С‚Рѕ `dashboard.chroma.count=229` РїСЂРё `blocks=247` РјРѕР¶РµС‚ Р±С‹С‚СЊ Р·Р°РјР°СЃРєРёСЂРѕРІР°РЅ historical proof (`247`) Рё РґР°С‚СЊ Р»РѕР¶РЅС‹Р№ green readiness signal.

Decision: РґР»СЏ post-apply readiness gate РґРµР№СЃС‚РІСѓРµС‚ strict live contract: historical/local proof РёСЃРїРѕР»СЊР·СѓРµС‚СЃСЏ С‚РѕР»СЊРєРѕ РєР°Рє РґРёР°РіРЅРѕСЃС‚РёС‡РµСЃРєРѕРµ evidence Рё РЅРёРєРѕРіРґР° РЅРµ РјРѕР¶РµС‚ РїРµСЂРµРІРµСЃС‚Рё `dashboard_chroma_count_mismatch` РІ `passed`. РџСЂРё live mismatch СЃС‚Р°С‚СѓСЃ РѕР±СЏР·Р°РЅ Р±С‹С‚СЊ `blocked_chroma_count_mismatch` СЃ РёС‚РѕРіРѕРј `done_with_chroma_count_blocker`.

Consequences: readiness Рє Diagnostic Center РѕСЃС‚Р°С‘С‚СЃСЏ С‡РµСЃС‚РЅРѕ Р·Р°Р±Р»РѕРєРёСЂРѕРІР°РЅРЅРѕР№ РґРѕ reconciliation/recovery С€Р°РіР°; СѓСЃС‚СЂР°РЅСЏРµС‚СЃСЏ СЂРёСЃРє Р»РѕР¶РЅРѕРїРѕР»РѕР¶РёС‚РµР»СЊРЅРѕРіРѕ gate-pass РёР·-Р·Р° stale Р°СЂС‚РµС„Р°РєС‚РѕРІ.



## ADR-029 - Dashboard Chroma total must use collection.count() as authoritative source

Status: accepted

Context: РІ HF4 РїРѕСЃР»Рµ controlled reindex direct Chroma diagnostic СѓР¶Рµ РїРѕРєР°Р·С‹РІР°Р» `247`, РЅРѕ dashboard РІСЂРµРјРµРЅРЅРѕ РѕС‚РѕР±СЂР°Р¶Р°Р» `0` РёР·-Р·Р° РІС‹С‡РёСЃР»РµРЅРёСЏ total С‡РµСЂРµР· `collection.get()` РІС‹Р±РѕСЂРєСѓ, С‡С‚Рѕ РґР°РІР°Р»Рѕ runtime drift.

Decision: РґР»СЏ admin/dashboard runtime total Chroma count Р±РµСЂС‘С‚СЃСЏ РёР· `collection.count()`; РІС‹Р±РѕСЂРєР° `get(..., include=['metadatas'])` РёСЃРїРѕР»СЊР·СѓРµС‚СЃСЏ С‚РѕР»СЊРєРѕ РґР»СЏ СЂР°СЃРїСЂРµРґРµР»РµРЅРёР№/СЃРѕСЃС‚Р°РІРѕРІ Рё РЅРµ РєР°Рє РёСЃС‚РѕС‡РЅРёРє total.

Consequences: dashboard Chroma total СЃРёРЅС…СЂРѕРЅРёР·РёСЂРѕРІР°РЅ СЃ direct diagnostic Рё strict gate, СѓРјРµРЅСЊС€Р°РµС‚СЃСЏ СЂРёСЃРє Р»РѕР¶РЅРѕРіРѕ blocker/passed СЃС‚Р°С‚СѓСЃР° РёР·-Р·Р° РѕСЃРѕР±РµРЅРЅРѕСЃС‚РµР№ РІС‹Р±РѕСЂРєРё API.



## ADR-030 - Diagnostic Center is a map-making layer, not a user-facing agent

Status: accepted

Context: РїСЂРѕРµРєС‚ РїРµСЂРµС€С‘Р» Рє Diagnostic Center РїРѕСЃР»Рµ readiness-gates, РЅРѕ РµСЃС‚СЊ СЂРёСЃРє РїСЂРµРІСЂР°С‚РёС‚СЊ РЅРѕРІС‹Р№ СЃР»РѕР№ РІ РѕС‚РґРµР»СЊРЅРѕРіРѕ user-facing LLM-Р°РіРµРЅС‚Р°, РєРѕС‚РѕСЂС‹Р№ РЅР°С‡РЅС‘С‚ РїРёСЃР°С‚СЊ РїРѕР»СЊР·РѕРІР°С‚РµР»СЋ, РїРѕРґРјРµРЅСЏС‚СЊ Writer Рё РїСЂРёРЅРёРјР°С‚СЊ authority-СЂРµС€РµРЅРёСЏ РїРѕ KB/governance.

Decision: Diagnostic Center v1 Р·Р°РєСЂРµРїР»С‘РЅ РєР°Рє internal map-making layer. РћРЅ СЃРѕР±РёСЂР°РµС‚ `DiagnosticCenterOutput` РёР· СЃСѓС‰РµСЃС‚РІСѓСЋС‰РёС… СЃРёРіРЅР°Р»РѕРІ (State Analyzer / Thread Manager / Context Assembly / governed retrieval metadata) Рё С„РѕСЂРјРёСЂСѓРµС‚ `working_hypothesis + next_micro_shift`. Diagnostic Center РЅРµ РіРµРЅРµСЂРёСЂСѓРµС‚ С„РёРЅР°Р»СЊРЅС‹Р№ РїРѕР»СЊР·РѕРІР°С‚РµР»СЊСЃРєРёР№ С‚РµРєСЃС‚, РЅРµ С†РёС‚РёСЂСѓРµС‚ KB РЅР°РїСЂСЏРјСѓСЋ, РЅРµ РјРµРЅСЏРµС‚ governance authority Рё РЅРµ РІРєР»СЋС‡Р°РµС‚СЃСЏ РІ active runtime Р±РµР· РѕС‚РґРµР»СЊРЅРѕРіРѕ PRD.

Consequences: РґРёР°РіРЅРѕСЃС‚РёС‡РµСЃРєР°СЏ Р»РѕРіРёРєР° СЃС‚Р°РЅРѕРІРёС‚СЃСЏ С‚РµСЃС‚РёСЂСѓРµРјРѕР№ РЅРµР·Р°РІРёСЃРёРјРѕ РѕС‚ Writer, runtime СЃРѕС…СЂР°РЅСЏРµС‚ multiagent-РґРёСЃС†РёРїР»РёРЅСѓ, Р° СЃР»РµРґСѓСЋС‰РёР№ С€Р°Рі (`PRD-046.1.1`) РјРѕР¶РµС‚ РїРѕРґРєР»СЋС‡Р°С‚СЊ СЃР»РѕР№ С‚РѕР»СЊРєРѕ РІ shadow-mode СЃ РѕС‚РґРµР»СЊРЅС‹РјРё eval/gate РїСЂРѕРІРµСЂРєР°РјРё.



## ADR-031 - Diagnostic Center shadow mode cannot affect user-facing output

Status: accepted

Context: РІ `PRD-046.1.1` Diagnostic Center РІРїРµСЂРІС‹Рµ РїРѕРґРєР»СЋС‡Р°РµС‚СЃСЏ Рє runtime. Р‘РµР· Р¶С‘СЃС‚РєРёС… РѕРіСЂР°РЅРёС‡РµРЅРёР№ shadow path РјРѕРі Р±С‹ РЅРµР·Р°РјРµС‚РЅРѕ РїРѕРІР»РёСЏС‚СЊ РЅР° WriterContract, writer prompt РёР»Рё final answer.

Decision: Diagnostic Center РІ runtime РґРѕРїСѓСЃРєР°РµС‚СЃСЏ С‚РѕР»СЊРєРѕ РІ trace-only shadow СЂРµР¶РёРјРµ. Shadow output СЃС‚СЂРѕРёС‚СЃСЏ РЅР° СЂРµР°Р»СЊРЅС‹С… runtime СЃРёРіРЅР°Р»Р°С…, РЅРѕ РЅРµ РїРµСЂРµРґР°С‘С‚СЃСЏ РІ WriterContract, РЅРµ РјРµРЅСЏРµС‚ writer prompt, РЅРµ РјРµРЅСЏРµС‚ validation path Рё РЅРµ РІР»РёСЏРµС‚ РЅР° final answer. РџСЂРё РѕС€РёР±РєРµ shadow runtime РїСЂРѕРґРѕР»Р¶Р°РµС‚ РѕСЃРЅРѕРІРЅРѕР№ РѕС‚РІРµС‚ Р±РµР· Р±Р»РѕРєРёСЂРѕРІРєРё.

Consequences: СЃРёСЃС‚РµРјР° РїРѕР»СѓС‡Р°РµС‚ РёР·РјРµСЂРёРјС‹Рµ divergence-РјРµС‚СЂРёРєРё РґР»СЏ СЃР»РµРґСѓСЋС‰РµРіРѕ PRD, СЃРѕС…СЂР°РЅСЏСЏ РёРЅРІР°СЂРёР°РЅС‚С‹ user-path Р±РµР·РѕРїР°СЃРЅРѕСЃС‚Рё (`writer_contract_changed=false`, `writer_prompt_changed_by_shadow=false`, `final_answer_changed_by_shadow=false`).



## ADR-032 - Planner Bridge remains shadow-only until explicit compliance integration PRD

Status: accepted

Context: РїРѕСЃР»Рµ trace-only Diagnostic Center shadow РїРѕСЏРІРёР»СЃСЏ СЂР°Р±РѕС‡РёР№ РїСѓС‚СЊ РЅРѕСЂРјР°Р»РёР·Р°С†РёРё СЃРёРіРЅР°Р»РѕРІ РІ candidate planning constraints, РЅРѕ РїСЂСЏРјРѕРµ РїРѕРґРєР»СЋС‡РµРЅРёРµ Рє Writer Move Compliance Р±РµР· divergence-РєР°Р»РёР±СЂРѕРІРєРё Рё РѕС‚РґРµР»СЊРЅРѕРіРѕ integration PRD СѓРІРµР»РёС‡РёРІР°РµС‚ СЂРёСЃРє user-path regressions.

Decision: Planner Bridge v1 СЂРµР°Р»РёР·СѓРµС‚СЃСЏ С‚РѕР»СЊРєРѕ РєР°Рє shadow/eval contract СЃР»РѕР№. РћРЅ РјРѕР¶РµС‚ С„РѕСЂРјРёСЂРѕРІР°С‚СЊ candidate constraints Рё trace, РЅРѕ `apply_to_writer=false`, `apply_to_writer_contract=false`, `activation_mode=shadow_only` РґРѕ РѕС‚РґРµР»СЊРЅРѕРіРѕ PRD-046.1.3.

Consequences: Р°СЂС…РёС‚РµРєС‚СѓСЂР° РїРѕР»СѓС‡Р°РµС‚ РіРѕС‚РѕРІС‹Р№ РјРѕСЃС‚ РґР»СЏ СЃР»РµРґСѓСЋС‰РµРіРѕ С€Р°РіР° РёРЅС‚РµРіСЂР°С†РёРё, СЃРѕС…СЂР°РЅСЏСЏ no-user-path-effect Рё РїСЂРµРґРѕС‚РІСЂР°С‰Р°СЏ РїСЂРµР¶РґРµРІСЂРµРјРµРЅРЅРѕРµ РІР»РёСЏРЅРёРµ Diagnostic Center/Planner Bridge РЅР° final answer.



## ADR-033 - Planner Bridge can compare with Writer Move Compliance only in shadow_compare mode

Status: accepted

Context: РїРѕСЃР»Рµ PRD-046.1.2/046.1.2-HF1 РїСЂРѕРµРєС‚Сѓ РЅСѓР¶РЅРѕ СЃСЂР°РІРЅРёС‚СЊ candidate constraints Planner Bridge СЃ С‚РµРєСѓС‰РёРјРё Writer Move Compliance rules, РЅРѕ Р±РµР· СЂРёСЃРєР° СЃРєСЂС‹С‚РѕРіРѕ РІР»РёСЏРЅРёСЏ РЅР° WriterContract/prompt/final answer.

Decision: РІРІРѕРґРёС‚СЃСЏ С‚РѕР»СЊРєРѕ shadow compare integration: Planner Bridge candidate + compliance comparison РїРёС€СѓС‚СЃСЏ РІ runtime trace РєР°Рє `planner_bridge_compliance_shadow`, РїСЂРё СЌС‚РѕРј `apply_to_writer=false`, `apply_to_writer_contract=false`, writer prompt Рё final answer path РѕСЃС‚Р°СЋС‚СЃСЏ РЅРµРёР·РјРµРЅРЅС‹РјРё.

Consequences: СЃРёСЃС‚РµРјР° РїРѕР»СѓС‡Р°РµС‚ РёР·РјРµСЂРёРјС‹Р№ compatibility СЃР»РѕР№ (compatible/tightens/expected_divergence/needs_review/blocked) Рё РіРѕС‚РѕРІРЅРѕСЃС‚СЊ Рє СЃР»РµРґСѓСЋС‰РµРјСѓ controlled pilot PRD, РЅРµ РЅР°СЂСѓС€Р°СЏ user-path safety gates.



## ADR-034 - Writer-Contract Pilot remains non-mutating until offline replay PRD

Status: accepted

Context: РїРѕСЃР»Рµ PRD-046.1.3 РїРѕСЏРІРёР»Р°СЃСЊ РіРѕС‚РѕРІРЅРѕСЃС‚СЊ СЃС‚СЂРѕРёС‚СЊ candidate constraints РґР»СЏ WriterContract, РЅРѕ РїСЂСЏРјРѕРµ РїСЂРёРјРµРЅРµРЅРёРµ overlay Рє production Writer path РІ СЌС‚РѕРј С†РёРєР»Рµ СЃРѕР·РґР°С‘С‚ СЂРёСЃРє РЅРµР·Р°РјРµС‚РЅС‹С… regressions РІ prompt/final answer.

Decision: РІ PRD-046.1.4 РІРІРѕРґРёС‚СЃСЏ С‚РѕР»СЊРєРѕ controlled pilot overlay (`pilot_shadow_only`) СЃ С„РёРєСЃРёСЂРѕРІР°РЅРЅС‹РјРё guardrails: `apply_to_writer_contract=false`, `apply_to_writer_prompt=false`, `apply_to_final_answer=false`. Pilot РѕР±СЏР·Р°РЅ РґРѕРєР°Р·С‹РІР°С‚СЊ immutability С‡РµСЂРµР· deterministic hash (`before/after`) Рё СЃРѕС…СЂР°РЅСЏС‚СЊ runtime trace/eval artifacts Р±РµР· provider calls.

Consequences: Diagnostic Center/Planner Bridge РїРѕР»СѓС‡Р°СЋС‚ РёР·РјРµСЂРёРјС‹Р№ РєРѕРЅС‚СЂР°РєС‚РЅС‹Р№ РјРѕСЃС‚ Рє Writer Р±РµР· production activation; СЃР»РµРґСѓСЋС‰РёР№ С€Р°Рі РґРѕРїСѓСЃРєР°РµС‚СЃСЏ С‚РѕР»СЊРєРѕ РєР°Рє offline replay/eval PRD (PRD-046.1.5), Р° РЅРµ РїСЂСЏРјРѕРµ РІР»РёСЏРЅРёРµ РЅР° РїРѕР»СЊР·РѕРІР°С‚РµР»СЊСЃРєРёР№ РѕС‚РІРµС‚.



## ADR-035 - Writer Prompt Replay remains offline-only before any prompt activation

Status: accepted

Context: РїРѕСЃР»Рµ PRD-046.1.4 РїРѕСЏРІРёР»Р°СЃСЊ РІРѕР·РјРѕР¶РЅРѕСЃС‚СЊ РѕС†РµРЅРёРІР°С‚СЊ candidate constraints РЅР° СѓСЂРѕРІРЅРµ prompt-context, РЅРѕ Р»СЋР±РѕРµ РїСЂСЏРјРѕРµ РїРѕРґРєР»СЋС‡РµРЅРёРµ replay-РєР°РЅРґРёРґР°С‚Р° РІ production Writer path РїСЂРµР¶РґРµРІСЂРµРјРµРЅРЅРѕ Рё СЂРёСЃРєРѕРІР°РЅРЅРѕ Р±РµР· РѕС‚РґРµР»СЊРЅРѕРіРѕ controlled rollout.

Decision: РІ PRD-046.1.5 replay СЃР»РѕР№ РѕРіСЂР°РЅРёС‡РµРЅ `offline_replay_only`: baseline Рё candidate prompt-context СЃСЂР°РІРЅРёРІР°СЋС‚СЃСЏ РґРµС‚РµСЂРјРёРЅРёСЂРѕРІР°РЅРЅРѕ (safety/KB/conflict/prompt-bloat/non-mutation), РЅРѕ replay РЅРµ РёРјРµРµС‚ РїСЂР°РІР° РјРµРЅСЏС‚СЊ production WriterContract, writer prompt РёР»Рё final answer Рё РЅРµ РІС‹Р·С‹РІР°РµС‚ provider.

Consequences: РїСЂРѕРµРєС‚ РїРѕР»СѓС‡Р°РµС‚ РёР·РјРµСЂРёРјС‹Р№ quality-eval С„СѓРЅРґР°РјРµРЅС‚ РґР»СЏ СЃР»РµРґСѓСЋС‰РµРіРѕ РѕРіСЂР°РЅРёС‡РµРЅРЅРѕРіРѕ runtime-СЌРєСЃРїРµСЂРёРјРµРЅС‚Р° (PRD-046.1.6) СЃ Р¶С‘СЃС‚РєРёРјРё rollback/safety gates РІРјРµСЃС‚Рѕ РЅРµРјРµРґР»РµРЅРЅРѕР№ Р°РєС‚РёРІР°С†РёРё РґР»СЏ РІСЃРµС… РїРѕР»СЊР·РѕРІР°С‚РµР»РµР№.



## ADR-036 - Prompt Constraint Pilot can affect Writer prompt only under default-off allowlisted runtime flag

Status: accepted

Context: РїРѕСЃР»Рµ offline replay (PRD-046.1.5) РЅСѓР¶РµРЅ РѕРіСЂР°РЅРёС‡РµРЅРЅС‹Р№ runtime-СЌРєСЃРїРµСЂРёРјРµРЅС‚ РґР»СЏ РїСЂРѕРІРµСЂРєРё prompt constraints, РЅРѕ broad activation РІ production СЃРѕР·РґР°С‘С‚ СЂРёСЃРє user-path regressions.

Decision: РІ PRD-046.1.6 pilot constraints РјРѕРіСѓС‚ РІР»РёСЏС‚СЊ РЅР° Writer prompt С‚РѕР»СЊРєРѕ РїСЂРё explicit runtime-С„Р»Р°РіР°С… (`PROMPT_CONSTRAINT_PILOT_ENABLED=true`, `PROMPT_CONSTRAINT_PILOT_MODE=test_apply`), С‚РѕР»СЊРєРѕ РґР»СЏ allowlisted/test users Рё С‚РѕР»СЊРєРѕ РїРѕСЃР»Рµ passed gates (rollback/safety/KB/conflict/prompt-bloat/non-mutation). РџРѕ СѓРјРѕР»С‡Р°РЅРёСЋ РїСѓС‚СЊ РѕСЃС‚Р°С‘С‚СЃСЏ disabled/shadow; `PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED=true` РёРјРµРµС‚ Р°Р±СЃРѕР»СЋС‚РЅС‹Р№ rollback-РїСЂРёРѕСЂРёС‚РµС‚.

Consequences: production default path РѕСЃС‚Р°С‘С‚СЃСЏ РЅРµРёР·РјРµРЅРЅС‹Рј, runtime-СЌРєСЃРїРµСЂРёРјРµРЅС‚ С‚СЂР°СЃСЃРёСЂСѓРµС‚СЃСЏ Р°СЂС‚РµС„Р°РєС‚Р°РјРё Рё РјРѕР¶РµС‚ Р±С‹С‚СЊ РјРіРЅРѕРІРµРЅРЅРѕ РѕС‚РєР»СЋС‡С‘РЅ rollback-С„Р»Р°РіРѕРј; broad rollout Р·Р°РїСЂРµС‰С‘РЅ РґРѕ РѕС‚РґРµР»СЊРЅРѕРіРѕ PRD-046.1.7+.



## ADR-037 - Diagnostic Center v1 accepted as governed shadow layer; runtime authority expansion requires separate PRD

Status: accepted

Context: РїРѕСЃР»Рµ PRD-046.1.15 Diagnostic Center v1 Рё СЃРІСЏР·Р°РЅРЅС‹Р№ Planner/Prompt-Constraint СЃС‚РµРє СЃС‚Р°Р±РёР»РёР·РёСЂРѕРІР°РЅС‹, РЅРѕ РѕСЃС‚Р°СЋС‚СЃСЏ СЂРёСЃРєРё РїСЂРµР¶РґРµРІСЂРµРјРµРЅРЅРѕРіРѕ СЂР°СЃС€РёСЂРµРЅРёСЏ authority РІ production user-path.

Decision: PRD-046.1.16 Р·Р°РєСЂРµРїР»СЏРµС‚ Diagnostic Center v1 РєР°Рє РІРЅСѓС‚СЂРµРЅРЅРёР№ governed shadow/runtime-governance СЃР»РѕР№ СЃ РїРѕСЃС‚РѕСЏРЅРЅС‹РјРё regression blockers. Broad rollout, РёР·РјРµРЅРµРЅРёРµ Writer prompt/contract/final answer path Рё СЂР°СЃС€РёСЂРµРЅРёРµ runtime authority Р·Р°РїСЂРµС‰РµРЅС‹ Р±РµР· РѕС‚РґРµР»СЊРЅРѕРіРѕ future PRD СЃ РЅРѕРІС‹Рј controlled rollout, rollback plan Рё normal-user no-effect РґРѕРєР°Р·Р°С‚РµР»СЊСЃС‚РІР°РјРё.

Consequences: РїСЂРѕРµРєС‚ РїРѕР»СѓС‡Р°РµС‚ С„РѕСЂРјР°Р»СЊРЅРѕ Р·Р°РєСЂС‹С‚С‹Р№ runtime governance boundary (`trace_only_shadow`, `default_off_limited_allowlisted_test_path`) Рё СЃС‚Р°Р±РёР»СЊРЅСѓСЋ РѕРїРѕСЂСѓ РґР»СЏ СЃР»РµРґСѓСЋС‰РµРіРѕ С€Р°РіР° РєР°С‡РµСЃС‚РІР° РѕС‚РІРµС‚РѕРІ (PRD-046.1.17) Р±РµР· РѕСЃР»Р°Р±Р»РµРЅРёСЏ safety/KB/privacy/no-mutation РёРЅРІР°СЂРёР°РЅС‚РѕРІ.



## ADR-038 - Response quality eval must pass before any Diagnostic Center runtime authority expansion

Status: accepted

Context: РїРѕСЃР»Рµ PRD-046.1.16 РїСЂРѕРµРєС‚ РїРѕРґС‚РІРµСЂРґРёР» governance/safety/no-mutation boundaries, РЅРѕ СЌС‚Рѕ РЅРµ РѕС‚РІРµС‡Р°РµС‚ РЅР° РІРѕРїСЂРѕСЃ РєР°С‡РµСЃС‚РІР° РїРѕР»СЊР·РѕРІР°С‚РµР»СЊСЃРєРѕРіРѕ РѕС‚РІРµС‚Р° РІ Р¶РёРІРѕР№ С‚СЂР°РµРєС‚РѕСЂРёРё.

Decision: РїРµСЂРµРґ Р»СЋР±С‹Рј СЂР°СЃС€РёСЂРµРЅРёРµРј РІР»РёСЏРЅРёСЏ Diagnostic Center/Planner/Prompt-Constraint РЅР° Writer/final-answer path РѕР±СЏР·Р°С‚РµР»РµРЅ РІРѕСЃРїСЂРѕРёР·РІРѕРґРёРјС‹Р№ offline response-quality eval pack (curated live-like scenarios + rubric + weak/hard-fail detection + KB/internal lens boundary checks).

Consequences: РѕР±СЃСѓР¶РґРµРЅРёРµ runtime authority expansion РїРµСЂРµРЅРѕСЃРёС‚СЃСЏ С‚РѕР»СЊРєРѕ РїРѕСЃР»Рµ СѓСЃРїРµС€РЅРѕРіРѕ quality evidence СЃР»РѕСЏ; РїСЂРёРѕСЂРёС‚РµС‚РѕРј СЃС‚Р°РЅРѕРІСЏС‚СЃСЏ continuity/depth-fit/micro-shift/non-bookishness Рё СЃРѕС…СЂР°РЅРµРЅРёРµ KB boundaries Р±РµР· broad rollout.



## ADR-039 - Controlled runtime pilot requires readiness plan and rollback-first governance



- Date: 2026-05-18

- Status: accepted

- Context: ????? PRD-046.1.16/046.1.17/046.1.18 ??????? ?????? ? ????????????? pilot only ??? ??????? governance, ?? ?????? runtime execution ??? ???????????????? readiness-planning ???????? ???? ????????? normal-user path, KB boundary violations ? ??????????????? rollback.

- Decision: ????? controlled runtime pilot ??? Diagnostic Center / Prompt-Constraint path ?????? ?????????? ? ?????????? plan-only readiness PRD, ??????? ?????????: cohort policy, toggle matrix, runtime preflight requirements, limited live smoke plan, rollback-first runbook, hard-stop criteria, monitoring artifact contract, normal-user guard, KB governance guard ? trace sanitization guard. Execution ??????????? ?????? ? ????????? ????????? PRD ????? ??????????? readiness gate.

- Consequences: Broad rollout ???????? ???????????; normal-user apply ???????? ??????????? ?? ?????????; rollback ???????? ?????????? ??????????? ????? FORCE_DISABLED; ?????????? readiness artifacts ????????? blocker ??? execution PRD.



## ADR-040 - Every controlled runtime execution must be followed by a no-new-execution results gate



- Date: 2026-05-18

- Status: accepted

- Context: after a single controlled execution window, direct cohort expansion without consolidated evidence review can hide rollback drift, normal-user side effects, trace hygiene regressions, or safety/KB boundary violations.

- Decision: each controlled runtime execution PRD must be followed by a dedicated no-new-execution results gate PRD that deterministically audits source evidence (execution scope, rollback, normal-user no-effect, quality delta, safety/KB, trace sanitization, no-mutation, encoding hygiene) and produces a decision gate: `continue_limited_candidate | fix_required | stop_pilot`.

- Consequences: rollout progression becomes evidence-first and reversible, broad rollout remains prohibited by default, and any further runtime execution requires an explicit next PRD with preserved rollback-first governance.



## ADR-041 - BotDB recovery closure requires live query proof before Diagnostic Center continuation



Status: accepted

Context: HF1 restored Chroma counts but left `/api/query` and bot retrieval path ambiguous due live runtime drift.

Decision: Diagnostic Center continuation is blocked until live proof confirms `dashboard=ok/247`, `registry_stats=200/247`, `/api/query=200` with hits, and bot retrieval path uses API without semantic fallback/circuit-open state.

Consequences: runtime truth is anchored in live artifacts; continuation PRDs cannot rely on historical/local-only Chroma evidence.



## ADR-042 - Registry cleanup uses focus-only gate with Chroma absence proof

Status: accepted
Context: post-recovery runtime may keep stale non-focus registry rows, while direct Chroma source checks can fail with runtime binding errors.
Decision: non-focus deletion is allowed only when independent proof confirms absence from all_blocks and Chroma; focus source is always protected; delete API must not leak raw Chroma tracebacks.
Consequences: operator-facing registry can be safely reduced to focus-only state without risking production source loss or governance mutation.

## ADR-043 - Provider-backed continuation requires readiness-only gate before new execution

Status: accepted
Context: after PRD-046.1.21-HF3 recovery closure, Diagnostic Center can continue, but immediate provider-backed execution would couple live dependencies and runtime risk without refreshed rollout policy evidence.
Decision: PRD-046.1.22 is locked to readiness-only scope: validate source gates, validate live BotDB health (`dashboard=247/ok`, `registry=1`, `query=200`, no semantic fallback), and publish strict contracts (single synthetic allowlisted operator, normal-user controls, rollback-first, hard-stop criteria, KB boundary, trace sanitization) without provider execution.
Consequences: provider-backed execution remains prohibited in PRD-046.1.22 and can start only in a separate PRD-046.1.23 with explicit execution evidence, rollback proof, and hard-stop enforcement.

## ADR-044 - Provider-backed limited smoke execution is constrained to one allowlisted operator with rollback-first and no normal-user effect

Status: accepted
Context: readiness PRD-046.1.22 confirmed live dependencies and policy boundaries, but first real provider-backed execution required strict containment to prevent accidental rollout and user-path regressions.
Decision: PRD-046.1.23 execution is constrained to one synthetic allowlisted operator (`pilot_runtime_operator_001`), five fixed scenarios, provider budget `<=5`, mandatory normal-user controls (`>=2`) with zero apply effect, rollback-first toggles, hard-stop safety/KB/trace gates, and sanitized-only artifacts (no raw provider payload or secrets).
Consequences: provider-backed runtime path can be validated with real calls while preserving production governance boundaries; broad rollout and production-ready decisions remain explicitly blocked until a dedicated results/quality/rollback gate (PRD-046.1.24).

## ADR-045 - Every provider-backed execution must be followed by a no-new-execution results gate before cohort expansion

Status: accepted
Context: PRD-046.1.23 executed the first provider-backed limited smoke, but expanding cohort/execution immediately would risk hiding regressions in rollback, normal-user no-effect, safety/KB boundaries, trace/provider sanitization, and BotDB stability.
Decision: PRD-046.1.24 is mandatory as a deterministic post-run results gate that consumes prior artifacts only (no new provider calls, no new runtime execution, no production mutation) and emits one of `continue_limited_candidate | fix_required | stop_provider_backed_pilot`.
Consequences: rollout progression stays evidence-first and reversible; broad rollout remains prohibited and production-ready remains false until a separate future PRD passes after this gate.

## ADR-046 - Controlled cohort expansion requires cumulative provider-backed consolidation gate pass

Status: accepted
Context: РїРѕСЃР»Рµ РґРІСѓС… provider-backed limited smoke С†РёРєР»РѕРІ (`PRD-046.1.23`, `PRD-046.1.25`) Рё РѕРґРЅРѕРіРѕ post-run results gate (`PRD-046.1.24`) С‚СЂРµР±РѕРІР°Р»РѕСЃСЊ Р°СЂС…РёС‚РµРєС‚СѓСЂРЅРѕ Р·Р°С„РёРєСЃРёСЂРѕРІР°С‚СЊ РєРѕРЅСЃРѕР»РёРґР°С†РёРѕРЅРЅС‹Р№ decision gate РґРѕ СЂР°СЃС€РёСЂРµРЅРёСЏ РєРѕРіРѕСЂС‚С‹.
Decision: РїРµСЂРµРґ Р»СЋР±С‹Рј controlled cohort expansion РѕР±СЏР·Р°С‚РµР»РµРЅ cumulative consolidation PRD (`PRD-046.1.26`) Р±РµР· РЅРѕРІС‹С… provider calls/execution/mutation, РєРѕС‚РѕСЂС‹Р№ РґРµС‚РµСЂРјРёРЅРёСЂРѕРІР°РЅРЅРѕ РїРѕРґС‚РІРµСЂР¶РґР°РµС‚ source chain completeness, provider evidence continuity, normal-user no-effect, rollback-first, safety/KB boundary, trace/provider sanitization, BotDB stability, no-mutation Рё artifact hygiene. РўРѕР»СЊРєРѕ РїСЂРё `final_status=passed` Рё `decision=ready_for_controlled_cohort_expansion_prd` РґРѕРїСѓСЃРєР°РµС‚СЃСЏ СЃР»РµРґСѓСЋС‰РёР№ PRD СЂР°СЃС€РёСЂРµРЅРёСЏ РєРѕРіРѕСЂС‚С‹.
Consequences: СЂР°СЃС€РёСЂРµРЅРёРµ РїСЂРѕРІР°Р№РґРµСЂРЅРѕРіРѕ РїРёР»РѕС‚Р° РѕСЃС‚Р°С‘С‚СЃСЏ evidence-first Рё РѕР±СЂР°С‚РёРјС‹Рј; broad rollout/production-ready/normal-user activation РѕСЃС‚Р°СЋС‚СЃСЏ Р·Р°РїСЂРµС‰С‘РЅРЅС‹РјРё РґРѕ Р±СѓРґСѓС‰РёС… РѕС‚РґРµР»СЊРЅС‹С… gate PRD.

## ADR-047 - Controlled cohort expansion execution remains bounded and non-authoritative

Status: accepted
Context: РїРѕСЃР»Рµ `PRD-046.1.26` Р±С‹Р»Рѕ СЂР°Р·СЂРµС€РµРЅРѕ РїРµСЂРµР№С‚Рё РѕС‚ single-operator limited smoke Рє СЂР°СЃС€РёСЂРµРЅРЅРѕР№ allowlisted synthetic cohort execution, РЅРѕ СЃСѓС‰РµСЃС‚РІРѕРІР°Р» СЂРёСЃРє СЃРєСЂС‹С‚РѕРіРѕ РїРµСЂРµС…РѕРґР° Рє normal-user activation РёР»Рё РЅРµСЏРІРЅРѕРіРѕ СЂР°СЃС€РёСЂРµРЅРёСЏ runtime authority.
Decision: `PRD-046.1.27` Р·Р°РєСЂРµРїР»СЏРµС‚ execution boundary: С‚РѕР»СЊРєРѕ allowlisted synthetic cohort РёР· С‚СЂС‘С… РѕРїРµСЂР°С‚РѕСЂРѕРІ, provider budget `<=12`, РѕР±СЏР·Р°С‚РµР»СЊРЅС‹Рµ normal-user controls Р±РµР· apply/provider effects, rollback-first/hard-stop/safety-KB/trace/no-mutation gates Рё Р·Р°РїСЂРµС‚ broad rollout/production-ready/normal-user activation.
Consequences: РґР°Р¶Рµ РїСЂРё Р·РµР»С‘РЅРѕРј execution СЂРµР·СѓР»СЊС‚Р°С‚Рµ (`ready_for_final_acceptance_and_stabilization_prd`) Diagnostic Center РѕСЃС‚Р°С‘С‚СЃСЏ governed limited layer; СЂР°СЃС€РёСЂРµРЅРёРµ authority РІРѕР·РјРѕР¶РЅРѕ С‚РѕР»СЊРєРѕ С‡РµСЂРµР· СЃР»РµРґСѓСЋС‰РёР№ РѕС‚РґРµР»СЊРЅС‹Р№ acceptance/stabilization gate PRD.

## ADR-048 - Provider-backed Diagnostic Center phase accepted as governed limited-runtime candidate

Status: accepted
Context: РїРѕСЃР»Рµ РґРІСѓС… single-operator provider-backed cycles, cumulative consolidation Рё controlled cohort expansion (`PRD-046.1.23..PRD-046.1.27`) С‚СЂРµР±РѕРІР°Р»Р°СЃСЊ С„РёРЅР°Р»СЊРЅР°СЏ Р°СЂС…РёС‚РµРєС‚СѓСЂРЅР°СЏ РїСЂРёС‘РјРєР° Р±РµР· РЅРѕРІРѕРіРѕ execution/call budget СЂРѕСЃС‚Р°.
Decision: `PRD-046.1.28` С„РёРєСЃРёСЂСѓРµС‚ phase acceptance РєР°Рє `accepted_as_governed_limited_runtime_candidate` РїСЂРё РѕР±СЏР·Р°С‚РµР»СЊРЅС‹С… permanent regression gates (normal-user no-effect, rollback-first, safety/KB boundary, trace/provider sanitization, no-mutation, encoding hygiene, BotDB stability, quality/micro-shift) Рё РїСЂРё Р¶С‘СЃС‚РєРёС… boundary-С„Р»Р°РіР°С…: `broad_rollout=false`, `production_ready=false`, `normal_user_activation=false`.
Consequences: provider-backed phase Р·Р°РІРµСЂС€РµРЅР° РЅР° governance СѓСЂРѕРІРЅРµ, РЅРѕ broad rollout Рё production launch Р·Р°РїСЂРµС‰РµРЅС‹; СЃР»РµРґСѓСЋС‰РёР№ РѕР±СЏР·Р°С‚РµР»СЊРЅС‹Р№ С€Р°Рі вЂ” `PRD-046.1.29` stabilization/cleanup/eval-harness consolidation РїРµСЂРµРґ Р»СЋР±С‹Рј РґР°Р»СЊРЅРµР№С€РёРј СЂР°СЃС€РёСЂРµРЅРёРµРј.
## ADR-049 - Diagnostic Center Stabilization / Cleanup Boundary

Status: accepted
Context: provider-backed Diagnostic Center phase was accepted in `PRD-046.1.28`, but runtime/eval/docs artifacts remained mixed between active operations and historical evidence.
Decision: `PRD-046.1.29` establishes a manifest-first, reproducibility-preserving cleanup boundary: separate production runtime, permanent quality gates, and historical evidence; disallow physical deletion of runtime/eval-critical files in this PRD; require explicit follow-up PRD for any destructive cleanup.
Consequences: project navigation is compact and maintainable, permanent gates remain intact, and broad rollout continues to require a separate governance PRD.
Implementation proof: `PRD-046.1.29` merged in commit `70635e1` on `origin/main`.
## ADR-049 - Controlled Rollout Planning Boundary

Status: accepted
Context: Diagnostic Center accepted as governed limited-runtime candidate, but rollout execution remains sensitive to rollback, safety/KB, trace sanitization, and normal-user isolation risks.
Decision: controlled rollout execution requires a separate explicit PRD with allowlist-only cohort, rollback-first policy, hard-stop enforcement, permanent gate reuse, and strict normal-user no-effect proof.
Consequences: planning and execution are separated; broad rollout and production-ready declaration remain blocked in planning-only phase.
## ADR-050 - Controlled Rollout Execution Boundary

Status: accepted
Context: PRD-046.1.30 prepared plan-only rollout boundaries; PRD-046.1.31 executes the first controlled rollout window.
Decision: execution remains allowlist-only and rollback-first with strict hard-stop, provider budget cap, normal-user no-effect, BotDB stability, safety/KB boundary, trace sanitization, and no-mutation/hygiene gates.
Consequences: broad rollout, normal-user activation, and production-ready declaration remain prohibited; post-execution decisions must be taken by a separate consolidation/results PRD.

## ADR-051 - Controlled Rollout Results Gate Boundary

Status: accepted
Context: after `PRD-046.1.31` execution passed, a separate consolidation stage was required to verify rollback/safety/normal-user/no-mutation continuity and fix docs sync drift before any activation-readiness decision.
Decision: `PRD-046.1.32` is mandatory as a no-new-execution/no-provider-call results gate that consumes source evidence only, validates provider budget and safety boundaries, enforces normal-user no-effect and no-mutation proofs, and blocks progression when docs consistency remains stale.
Consequences: rollout governance stays evidence-first and reversible; broad rollout and normal-user activation remain prohibited; next step may only be readiness decision PRD (`PRD-046.1.33`) when this gate is fully green.

## ADR-052 - Limited runtime activation requires readiness/boundary gate before allowlisted live execution

Status: accepted
Context: after `PRD-046.1.32`, the project had green controlled-rollout results evidence, but broad rollout / normal-user activation / production-ready authority expansion remained prohibited and required an additional boundary decision before any live allowlisted execution.
Decision: before any allowlisted limited live activation, a dedicated readiness/boundary decision gate is mandatory (`PRD-046.1.33`) to confirm source evidence integrity, strict live dependencies, normal-user no-effect, rollback-first and hard-stop completeness, safety/KB boundary, trace/provider sanitization, no-mutation proof, artifact hygiene, and docs sync. The readiness PRD itself does not perform runtime execution or provider-backed activation.
Consequences: the next step can only be a separate constrained execution PRD (`PRD-046.1.34`) with allowlist, budget, rollback-first, and post-run results gating; broad rollout and production-ready declaration remain blocked pending future dedicated governance gates.
## ADR-053 - Creator-only live activation precedes external allowlist expansion

Status: accepted
Context: after `PRD-046.1.33`, limited runtime readiness was passed, but project state still has no external real users; broad rollout and normal-user activation remain prohibited.
Decision: first live activation step is constrained to `creator_only` runtime mode with explicit creator identity boundary, admin kill switch priority, strict normal-user no-effect controls, sanitized trace monitor, provider budget cap, and rollback/hard-stop governance. External allowlist expansion is deferred to later PRDs.
Consequences: this step is not broad rollout and not production-ready declaration; `broad_rollout_allowed=false`, `production_ready=false`, and `normal_user_activation_allowed=false` remain invariant.
## ADR-054 - Creator live continuation requires explicit evidence-strength gate

Status: accepted
Context: PRD-046.1.34 passed safety/runtime boundaries, but web chat smoke evidence can be probe-level or simulated without strong sanitized live-turn proof.
Decision: PRD-046.1.35 introduces a dedicated evidence-strength audit that classifies artifacts into `actual_live_turn_evidence`, `runtime_probe_evidence`, `simulated_gate_evidence`, and `missing_evidence`; continuation beyond creator-only stage is blocked when actual live-turn evidence is absent.
Consequences: safety-green is necessary but insufficient; rollout remains constrained until evidence quality is explicit and reproducible.

## ADR-055 - Creator live evidence requires end-to-end RAG delivery trace

Status: accepted
Context: PRD-046.1.35 ended with evidence_incomplete; we needed a strict chain proof from BotDB query to writer prompt and debug trace.
Decision: introduce HF1 scorecard + creator_live_turn_proof + rag_to_writer_delivery_proof with delivery classification and explicit governance-blocked state.
Consequences: creator-only runtime remains bounded; broad rollout and normal-user activation stay disabled until later PRDs.

## ADR-056 - Live RAG evidence must align adaptive trace, multiagent trace, and writer prompt

Status: accepted
Context: HF2 showed in-process retrieval success while strict live artifacts still reported zero delivery.
Decision: HF3 evaluates two live queries, aligns adaptive+multiagent traces, and stores explicit writer KB truncation audit as a non-blocking quality backlog.
Consequences: rollout remains bounded to creator-only path; broad rollout and normal-user activation stay disabled.

## PRD-046.1.35-HF4
Current Stage:
PRD-046.1.35-HF4 calibrated creator-live response behavior: example/explanation requests no longer trigger regulate_first by default, practice rejection suppresses body-action suggestions, and Web Trace displays non-empty safe Writer chunk previews.
Next:
PRD-046.1.36 Creator Live Pilot Acceptance / Minimal Admin Runtime Controls v1.

## HF4 Delivery Metadata
- prd_id: PRD-046.1.35-HF4
- commit_hash: 3a3c6a32a0c29551440432c0a266ab7cbab25b20
- push_status: pushed_to_origin_main

## ADR-055 - Diagnostic Center creator-live pilot acceptance boundary is completion-ready without broad rollout

Status: accepted
Context: HF4 passed behavior calibration and creator pipeline evidence, while broad rollout and production-ready declaration remain disallowed.
Decision: PRD-046.1.36 accepts Diagnostic Center as a governed creator-live pilot layer with runtime controls, rollback hard-stop, and strict normal-user no-effect boundary.
Consequences: next step is final completion decision gate (`PRD-046.1.37`), not broad rollout.

## ADR-057 - Diagnostic Center v1 completion gate closes current creator-pilot phase without rollout expansion

Status: accepted
Context: PRD-046.1.36 accepted creator-live pilot layer but left runtime readiness warning and mixed evidence provenance strengths.
Decision: PRD-046.1.37 enforces final source/provenance/runtime/live/admin/rollback/normal-user/safety/no-mutation decision package and closes Diagnostic Center v1 for the current phase.
Consequences: creator-only/allowlist pilot remains governed; broad rollout stays prohibited; production_ready remains false; next work moves to Multiagent Quality & Tuning Track.

## ADR-058 - Diagnostic Center admin controls are available for single-developer local governance without production rollout declaration

Status: accepted
Context: after PRD-046.1.37-HF1 completion, operational docs and admin control surface needed explicit synchronization to avoid ambiguity between local developer controls and production rollout policy.
Decision: PRD-046.1.38 introduces a dedicated Diagnostic Center admin contract (`effective/control/reset`) and Web Admin tab with full mode visibility, including `developer_local_all_users`, while preserving strict boundary flags (`production_ready=false`, `broad_rollout_allowed=false`, `normal_user_activation_allowed=false`, `external_users_allowed=false`).
Consequences: single-developer local operations can exercise full runtime control map with auditable state, but production authority expansion remains blocked until a separate future governance PRD.

## ADR-059 - Known internal concepts must be answered from governed KB grounding before asking the user to define the term

Status: accepted
Context: live multiagent failures showed that Writer could ask clarifying questions about already-known internal concepts (for example, `РЅРµР№СЂРѕСЃС‚Р°Р»РєРёРЅРі`) even when retrieval/context already contained grounding.
Decision: introduce deterministic Knowledge Answer Routing Guard before Writer contract. If user asks/challenges a known internal concept and KB grounding is available (including lexical near-exact fallback), runtime sets `knowledge_answer_first`, disables definition-first behavior, and blocks practice-first diversion for that turn.
Consequences: concept questions are answered from internal governed meaning first, trace explicitly records `knowledge_answer` and `practice_gate`, and future tuning can iterate on measurable failure-case baseline instead of subjective chat impressions.

## ADR-059 Amendment - Acceptance requires final-answer compliance, not only guard flags

Status: accepted
Context: PRD-047.0 showed a false-positive gap where internal guard flags were correct but final user-facing answers still violated known-concept and no-practice expectations.
Decision: quality acceptance for known-concept routing is valid only when evaluator checks final answer text (forbidden fragments, clarification-question bans, required semantics, practice gate behavior, and required grounding), not trace flags alone.
Consequences: failure baseline now rejects mismatched final answers even when internal trace appears green; next tuning PRDs can rely on stricter and reproducible acceptance evidence.

## ADR-060 - NEO Philosophy Kernel is an internal lens layer, not a user-facing quotation source

Status: accepted

Date: 2026-05-28

Context: PRD-047.1 required stable philosophical grounding for Writer without turning source materials into raw quote output or authority references in user-facing responses.

Decision: introduce versioned `NEO Philosophy Kernel` and `Writer Freedom Contract v1` as compact internal prompt/context layers. Kernel content is structured and short, selected deterministically per turn, and exposed in trace/admin only as sanitized metadata (no raw long source passages).

Consequences: Writer receives clearer identity/lens boundaries with guided freedom (`mode_is_hint_not_cage`, `practice_requires_gate`) while safety/hard-boundary governance remains strict. Future PRDs can tune depth/quality using measurable kernel fields without mutating KB authority or copying source text verbatim.

## ADR-060 Amendment - Philosophy Kernel acceptance requires answer-quality and prompt-compactness gates

Status: accepted

Date: 2026-05-28

Context: PRD-047.1 established structural kernel/freedom foundation, but quality acceptance still needed reproducible answer-level validation and prompt-size safeguards to avoid verbose or technical drift.

Decision: PRD-047.2 adds mandatory acceptance gates:
- reproducible kernel quality dataset (>=12 cases),
- answer-level evaluator over final text (not trace flags only),
- prompt compactness budgets for kernel/freedom sections,
- direct-run pass requirement (`12/12`) before acceptance.

Consequences: Philosophy Kernel governance now requires both structural correctness and measurable response quality/compactness; future expansions should build on this gate before dialogue continuity layers.

## ADR-061 - Active Line is a continuity layer; Diagnostic Center observes but does not rigidly command Writer

Status: accepted

Date: 2026-05-28

Context: live dialogue failures after PRD-047.2 showed repeated mechanical revoicing and unsolicited action-step drift even when kernel and practice gates were present.

Decision: introduce `Active Line / Dialogue Continuity v1` as lightweight deterministic layer (`active_line.py`) that computes per-turn intent/continuity/repair/revoicing/practice signals and passes them into Writer contract/prompt/compliance. Diagnostic Center and admin runtime surfaces expose this layer read-only; they do not become a rigid command system for Writer.

Consequences: dialogue continuity behavior becomes reproducible and testable (`dry/direct/live` runners), practice suppression is explicit on mechanism-first turns, correction turns use repair mode, and architecture keeps Writer freedom with bounded deterministic guardrails.

## ADR-062 - Response Planner v1 is deterministic next-meaningful-move layer, not a new answer-writing agent

Status: accepted

Date: 2026-05-28

Context: after PRD-047.3, continuity signals reduced drift, but Writer still needed compact per-turn guidance about answer shape/depth/question/practice behavior to keep one coherent move per turn without turning Writer into a rigid script.

Decision: add `Response Planner v1` as deterministic layer between Active Line and WriterContract. Planner does not call LLMs and does not produce user-facing text; it computes compact move/policy fields (`next_move`, `answer_shape`, `response_depth`, `question_policy`, `practice_policy`, `revoicing_policy`, `must_include`, `must_avoid`) from existing runtime signals. Safety, Knowledge Answer routing, and Practice Gate remain hard boundaries; Writer Freedom Contract remains active as guided style/freedom frame.

Consequences: turn-level move selection becomes reproducible and traceable (`debug/api/admin/runtime`), live acceptance can enforce strict no-fallback planner-trace policy, and future quality work can calibrate answer fit on measurable planner outputs without changing governance authority fields or adding a new LLM agent.

## ADR-063 - Planner quality acceptance requires answer-fit calibration on weak live groups, not planner-trace presence alone

Status: accepted

Date: 2026-05-28

Context: PRD-047.4 proved structural planner integration and trace visibility, but live cases still showed weak semantic fit (low-resource, safety-adjacent distress, defensive framing, close turns, no-question requests, explicit step requests, repair turns) despite formally valid planner fields.

Decision: PRD-047.5 introduces mandatory planner quality calibration with deterministic text-level override signals in `response_planner.py`, answer-level fit evaluator over final writer text, and strict runner acceptance across `dry/direct/live` with no runner-side live fallback.

Consequences: acceptance now requires both structural planner trace and behavioral fit between planner decision and final answer; planner remains deterministic and non-LLM, while Writer Freedom Contract remains active under stronger policy-obedience checks.

## ADR-064 - PRD-047.5-HF1 enforces strict planner-vs-final-answer obedience and closes safety-adjacent false positives

Status: accepted

Date: 2026-05-29

Context: post-acceptance audit of PRD-047.5 found a critical false-positive class: `response_planner` selected `stabilize_safety / safety_grounding`, but final answer drifted into mechanism/explanation text while evaluator still returned `passed=true`.

Decision: PRD-047.5-HF1 hardens answer-fit acceptance on final text with strict shape/policy checks and mismatch counters (`safety_grounding`, `short_support`, `question_policy=none`, `practice_policy=forbidden`, `planner_answer_shape_alignment`), keeps live runner planner source API-trace-only, and applies minimal writer compliance repair where strict evaluator exposed real runtime drift.

Consequences: acceptance evidence now rejects planner/answer mismatch in safety-adjacent and no-question paths; HF1 artifacts are green only when final answer obeys planner shape/policy (`dry=26/26`, `direct=26/26`, `live=26/26`).



## ADR-069 - PRD-047.11-AUDIT is evidence-first and may close as warning

Status: accepted

Date: 2026-06-02

Context: after PRD-047.11, previous dry/direct/live artifacts claimed writer-first acceptance, but live owner feedback still reported greeting over-analysis, stale mechanism phrases, and weak truthfulness between synthetic checks and real dialogue quality.

Decision:
- add a dedicated `PRD-047.11-AUDIT` runner/dataset/artifact pack focused on source inventory, acceptance-gate truthfulness, live case matrix, raw traces, and prompt canvases;
- treat missing browser proof (`playwright_not_installed`) and incomplete admin screenshot evidence as warning-grade audit outcomes, not silent passes;
- keep single runtime / single Writer / advisory-only Diagnostic Center intact during the audit;
- select the next repair PRD by strongest confirmed failure cluster, not by the easiest visible symptom.

Consequences:
- the runtime can remain in `warning` status even when the audit implementation itself is complete;
- stale bad-phrase detection becomes stricter and scans all turns/traces, reducing false-green reports;
- follow-up PRD selection is evidence-based (`PRD-047.11-HF1` before broader profile consolidation).

## ADR-070 - Writer-visible advisory sanitization after PRD-047.11-HF1

Status: accepted

Date: 2026-06-02

Context: PRD-047.11-AUDIT showed that `mvp_free_dialogue` still leaked legacy diagnostic/planner/active-line command pressure into the writer-visible prompt (`WRITER MOVE MUST DO`, raw practice suppression flags, planner must_include/must_avoid markers, and stale fallback phrases). The runtime needed a prompt-diet repair without adding a new mode, new agent, or stronger user-facing safety block.

Decision:
- keep `FINAL ANSWER DIRECTIVE` as the main writer-visible governing block;
- preserve raw diagnostic/planner/active-line data in trace/admin/evidence only;
- convert writer-visible legacy signals into a compact neutral advisory summary through `legacy_advisory_sanitizer_v1`;
- rewrite practice suppression semantics to `no_exercise_but_answer_normally`, meaning "no unsolicited exercise/practice suggestion" rather than "no substantive answer";
- keep bad phrase blocklists evaluation-only and remove stale template/fallback sources instead of steering Writer with blocklist instructions.

Consequences:
- Writer receives less imperative prompt pressure in `mvp_free_dialogue`, while observability remains intact;
- prompt canvases can be audited for absence of raw legacy command blocks without losing runtime debug detail;
- future UI/browser proof work can focus on rendering and evidence capture rather than prompt-assembly cleanup.

## ADR-071 - Fresh chat starts as a local context line until continuation or knowledge need is explicit

Status: accepted

Date: 2026-06-04

Context: live evidence after PRD-047.11-HF1 showed that a new greeting-only chat could still inherit stale mechanism/topic steering from prior sessions, producing over-analytical first answers and repair friction.

Decision:
- add deterministic `fresh_chat_context_policy_v1`;
- treat the first 1-2 turns of a new chat as local current-chat scope by default;
- block cross-session topic continuation on greeting/contact turns unless the user explicitly asks to continue a previous topic or asks a real knowledge/concept question;
- expose the policy in trace, live evidence, and admin runtime effective payload.

Consequences:
- fresh greetings no longer pull stale mechanism context into the active writer path;
- explicit continuation still re-enables cross-session grounding with auditable reasons;
- no new agent, no new runtime path, and no governance/KB mutation were introduced.

## ADR-072 - Writer-visible RAG must pass one final context package gate

Status: accepted

Date: 2026-06-04

Context: live prompt canvases showed a contradiction where retrieval could be classified as `memory_only` or `none`, yet raw `KNOWLEDGE RAG HITS` still leaked into the writer-visible prompt.

Decision:
- introduce `writer_context_package_v1` as the final assembly boundary for writer-visible context;
- allow trace/admin to retain `rag_candidates_for_trace`, but pass `rag_for_writer` only when the gate explicitly includes it;
- keep greeting repairs, short social/contact turns, and fresh-chat non-knowledge turns free from writer-visible raw RAG chunks;
- expose gate counts/reasons and runtime versions in admin effective payload and live evidence exports.

Consequences:
- retrieval observability remains intact without bypassing the writer-visible gate;
- real browser/live cases can verify both prompt hygiene and answer behavior on the same runtime path;
- the system stays unified: no duplicated orchestrator, no new guard branch, no KB/governance mutation.


## ADR-073 - Unified dialogue policy v2 consolidates preset modes and dialogue-state resolvers in one runtime path

Status: accepted

Date: 2026-06-05

Context: after the PRD-047.9..047.11 chain, `safe_guided` and `mvp_free_dialogue` still behaved like partially separate logic branches, while live follow-up failures (`РґР°`, repair complaint, style preference, repeated direct question, close ack) showed that Writer needed one explicit answer obligation instead of more phrase-specific patches.

Decision:
- keep one multiagent runtime path and normalize behavior through `unified_dialogue_policy_v2`;
- treat `safe_guided`, `free_dialogue_default`, and `mvp_free_dialogue` aliasing as preset resolution, not as separate orchestrators or API paths;
- introduce deterministic dialogue-state layers: `dialogue_act_resolver_v1`, `last_assistant_offer_v1`, `unanswered_question_tracker_v1`, `dialogue_style_state_v1`, and `answer_obligation_resolver_v1`;
- keep `final_answer_directive_v1` as the single Writer-facing control block and `writer_context_package_v1` as the single Writer context package;
- preserve advisory-only roles for Diagnostic Center / Planner / Active Line / Diagnostic Card and keep minimal safety boundaries hard.

Consequences:
- short follow-ups, repairs, confirmations, and style requests are handled through reusable runtime state instead of exact-text patches;
- Admin Runtime, live evidence, and browser/admin acceptance expose one coherent effective policy contract;
- no new LLM agent, no new runtime branch, no KB governance mutation, and no production rollout were introduced.

## ADR-074 - User-facing static replies are not allowed outside narrow safety/minimal-contact boundaries

Status: accepted

Date: 2026-06-08

Context: PRD-047.14-HF1.1 audited remaining hardcoded user-facing reply candidates after the active template-family fallback repair. The audit found active static explanation/repair/direct-answer candidates that can bypass Writer authorship if left as runtime answer factories.

Decision:
- keep Writer as the owner of semantic final answers;
- allow static user-facing text only for narrow safety or minimal-contact boundaries with trace evidence;
- treat repair/explanation/knowledge-answer stubs as candidates for targeted removal or conversion to Writer retry/contract signals;
- keep detector constants, test fixtures, historical artifacts, and docs outside the user-facing reply boundary;
- preserve audit-only no runtime mutation in PRD-047.14-HF1.1 and defer removal to `PRD-047.14-HF1.2`.

Consequences:
- no-stub boundary evidence is now explicit and reproducible;
- future cleanup must remove or convert active static reply factories without adding a new Writer/orchestrator branch;
- safety/minimal fallback exceptions remain narrow, documented, and auditable.

## ADR-074 Amendment - Static repair answers must become Writer retry/contract signals

Status: accepted

Date: 2026-06-08

Context: PRD-047.14-HF1.2 removed the high-confidence Writer-side static semantic repair class found by HF1.1 without replacing it with new canned text.

Decision:
- static user-facing repair or knowledge answers are not valid runtime fixes;
- when Writer output fails, runtime must provide feedback to Writer through existing gate/retry/directive signals or quarantine state effects;
- runtime may not replace Writer with a canned semantic answer;
- `no_stub_repair_signal_v1` is a control/observability signal only and must carry `user_facing_replacement_created=false`.

Consequences:
- final-answer authorship remains with Writer;
- failed repair attempts are retried or quarantined by the existing final-answer acceptance gate;
- remaining summary/advisory/static candidates require separate PRD scope instead of hidden in-place rewriting.

## ADR-075 - LLM-assisted retrieval composer requires trace evidence and deterministic pre-pass gating

Status: accepted

Date: 2026-06-09

Context: PRD-047.15 introduced deterministic `contextual_retrieval_query_composer_v1` and left a warning that mixed/low-confidence live dialogue cases require owner-trace calibration before any LLM assistance is designed.

Decision:
- keep Composer v1 deterministic until trace/owner evidence proves where LLM assistance is needed;
- require replay/live trace review, owner review sheet, and blocker gates before changing retrieval behavior;
- if LLM assistance is introduced later, default to a hybrid design: deterministic pre-pass handles high-confidence cases, LLM handles only low-confidence/mixed cases through strict metadata-only JSON;
- LLM Composer output must never contain final answers, advice text, canned explanations, or user-facing therapy phrases;
- Writer remains the only final answer author.

Consequences:
- HF1 can close as warning without runtime mutation because owner scores are pending;
- future hybrid work has a concrete evidence base and must preserve no-stub/no-new-runtime-path boundaries;
- heuristic-only tuning, hybrid assistance, or further owner review can be selected from trace metrics instead of subjective impressions.

## ADR-077 - Hybrid Retrieval visibility is a developer observability surface, not runtime authority

Status: accepted

Date: 2026-06-11

Context: PRD-047.15-HF2-R2 closed the gap between backend hybrid retrieval metadata and what the developer can actually see in Web Admin and Web Trace. The risk was to accidentally turn this visibility work into a second runtime authority layer or another legacy admin control center.

Decision:
- treat Hybrid Retrieval visibility as read-only developer observability;
- keep Writer as final answer author and keep planner metadata advisory;
- expose planner model/max tokens/mode plus planned/executed query metadata in Runtime, Web Trace, and compact trace summary;
- remove duplicate Advanced Controls sub-tabs from the primary admin surface and keep Compatibility as the only explicit legacy/read-only lane;
- move legacy runtime status such as dialogue-profile alias and knowledge-graph state into compatibility/read-only presentation instead of deleting backend knobs blindly.

Consequences:
- hybrid retrieval decisions are visible end-to-end without changing runtime behavior;
- Runtime tab becomes more trustworthy as an effective-state surface instead of a mixed editable legacy surface;
- future work can focus on retrieval quality and chunk metadata instead of more admin UI duplication.

## ADR-078 - Retrieval query assembly must be repaired before overlay-live evaluation resumes

Status: accepted

Date: 2026-06-17

Context: PRD-047.23 audited the full chain from Bot_data_base source/chunk/store/query through writer payload and Web Trace using the uploaded local trace plus live/local reproduction. The first suspicious Neurostalking cut did not prove a primary stored-chunk defect. The strongest repeated failure instead came from current-turn retrieval query pollution/duplication on follow-up knowledge questions, while payload/UI counter mismatches remained secondary observability debt.

Decision:
- prioritize retrieval query assembly repair before any new overlay-live evidence/evaluation PRD;
- treat the observed `...РёР·РЅСѓС‚СЂРё С‡РµРіРѕ С‚` case as a downstream preview/full-content ambiguity until a separate repair PRD proves otherwise;
- keep Bot_data_base source/chunk/Chroma untouched in this phase because the audit did not justify chunker mutation or reindex;
- keep payload-trace schema cleanup as secondary work after retrieval focus is repaired, unless a future blocker shows the trace mismatch itself changes user-path behavior.

Consequences:
- the next PRD should target current-turn focus, previous-topic contamination, duplicate fragment collapse, and executed/planned query cleanliness;
- overlay-live evaluation is deferred because it would otherwise validate polluted retrieval behavior instead of stable runtime behavior;
- chunking repair remains explicitly unapproved until a future PRD produces direct stored-boundary evidence.

## ADR-079 - Owner Web Chat pilot parity must use the same startup truth as automated proof

Status: accepted

Date: 2026-06-19

Context: PRD-047.27-HF1 proved semantic-card visibility in an automated runner, but owner Web Chat still showed disabled/cards 0 because the runner launched backend with SEMANTIC_CARDS_PILOT_ENABLED=true while the manual pilot startup path did not.

Decision:
- treat owner/manual Web Chat pilot startup and automated proof as the same runtime truth;
- keep SEMANTIC_CARDS_PILOT_ENABLED as the only pilot flag for semantic cards;
- do not add owner-only, admin-only, or web-trace-only semantic-card flags;
- extend the shared runtime trace with semantic-card identity fields instead of creating a parallel status surface;
- keep semantic cards advisory-only inside the existing writer_kb_payload_v1 path.

Consequences:
- Admin Runtime, Web Chat trace, and owner live proof now read the same pilot truth when local pilot startup is used;
- future cleanup should consolidate pilot toggles instead of multiplying runtime branches;
- semantic-card expansion is deferred until the unified runtime baseline is explicitly documented.

## ADR-080 - Owner trace must separate retrieval candidates from Writer-visible payload

Status: accepted

Date: 2026-06-24

Context: PRD-047.32 showed that owner Web Chat trace could be technically rich but semantically misleading. The UI label `Р§Р°РЅРєРё РІ Writer` rendered `memory.semantic_hits`, while actual Writer input came from `writer_kb_payload_v1` and sometimes contained a different semantic-card payload. Hybrid Planner shadow invalid JSON also looked like a production failure without scope.

Decision:
- introduce `runtime_truth_trace_v1` inside the existing Writer context/runtime trace path, not as a new runtime subsystem;
- treat retrieved candidates, filtered-out candidates, trace-only grounding, and Writer-visible payload as separate trace categories;
- make actual Writer payload provable through item ids, origin, chunk type, source doc, `sent_to_writer`, `writer_can_ignore`, `applied_as_authority`, and inclusion reason;
- keep diagnostic candidate lists visible, but label them as `Retrieval candidates / trace-only`;
- scope shadow/compatibility fallback fields with `fallback_scope`, `production_query_source`, and `production_answer_affected`.

Consequences:
- owner trace can explain why a chunk was found but not sent to Writer;
- semantic cards can be Writer-visible advisory payload without becoming authority;
- Hybrid Planner shadow failures remain observable without being confused with production answer failure;
- future cleanup should retire legacy/fallback fields only after trace taxonomy proves which ones are still active.

## ADR-081 - Latest-turn boundary proof must be a stable owner/debug contract, not an inferred side effect

Status: accepted

Date: 2026-07-02

Context: PRD-047.36-POST-HF showed that explicit `no_internal_db` and `no_practice` were already being honored in runtime behavior, but owner/debug trace could not prove that reliably because the evidence was split across `latest_turn_constraints_v1`, grounding reason strings, and nested runtime summary fields. The readiness runner then collapsed `boundary_flags` to empty even on correctly suppressed turns.

Decision:
- add a single stable `boundary_trace_v1` owner/debug contract;
- propagate it through final directive, writer context package, runtime truth trace, runtime summary, orchestrator debug payload, and debug API response;
- let runners and Web/owner tools read this contract first instead of reconstructing boundary state from incidental fields;
- keep the contract read-only and owner/debug only, without changing public answer wording or adding a new runtime path.

Consequences:
- explicit latest-turn boundaries become provable end-to-end for owner/debug inspection;
- readiness gates no longer depend on fragile field inference;
- runtime behavior, retrieval ranking, DB/Chroma state, and semantic-card authority remain unchanged.

## ADR-098 - Removal cleanup stays manifest-first, proof-first, and behavior-neutral

Status: accepted

Date: 2026-07-08

Delivery: PRD-047.40 accepted with warning across main commits `417113b` and `b954a52`.

Context: PRD-047.39 classified two cleanup classes but deliberately deferred execution: `532` raw log artifacts were still tracked in Git, and several dead legacy-bound tests still existed physically even though the runtime import graph no longer used the underlying modules. The main risk was over-cleanup: deleting evidence from disk, removing files without executable-import proof, or collapsing compatibility shims without runtime trace evidence.

Decision:
- manifest-approved raw artifacts may be removed from Git tracking only, not deleted from disk, and markdown evidence must remain tracked;
- dead legacy-bound tests may be physically removed only after repo-wide executable-import proof and matching `pytest.ini` ignore cleanup;
- cleanup verification must use positive proof (`test_dead_code_removed.py`), before/after regression evidence, and before/after live smoke rather than only negative assertions;
- `user_level_adapter` may be classified during cleanup, but if active compat surfaces still exist in runtime or API metadata, deletion is deferred to a separate PRD;
- cleanup PRDs must remain behavior-neutral unless a later PRD explicitly opens runtime mutation.

Consequences: the consolidation program can now remove dead baggage without destroying evidence or blurring runtime behavior changes into cleanup work. Future deletion of remaining compatibility shims or unrelated test-suite debt must come through their own narrowly scoped PRDs.
## ADR-100 - God-file decomposition must start with exact boundary mapping and snapshot guards, not direct code moves

Status: accepted

Date: 2026-07-09

Delivery: PRD-047.42 accepted in main commit `d62fa43`.

Context: PRD-047.39 classified god files as a real consolidation risk, and PRD-047.41 removed enough config uncertainty to inspect the biggest remaining files safely. The next danger was to start moving code inside `writer_agent.py`, `admin_routes.py`, or `writer_contract.py` based only on size and intuition, which would blur hidden contracts and make later regressions hard to attribute.

Decision:
- run a mapping-only Stage 1 before any decomposition mutates source files;
- map exact line ranges and responsibilities for `writer_agent.py`, `admin_routes.py`, and `writer_contract.py`;
- mark `legacy_compat` fragments explicitly rather than folding them silently into new modules;
- capture representative read-only snapshot contracts for `WriterContract.to_prompt_context`, `WriterAgent._resolve_runtime_settings`, `WriterAgent._enforce_answer_compliance`, and selected `admin_routes` handlers before moving code;
- keep the `19` production `diagnostic_center_*` files out of this PRD and defer them to a separate `PRD-047.42b` because their gate-heavy structure and caller graph form a different split problem;
- prohibit source mutation, signature changes, runtime-path changes, Writer/retrieval/safety/DB/Chroma/source mutation, and “fix while reading” opportunism in this stage.

Consequences: the repository now has an evidence-backed cut map for the three highest-priority non-diagnostic-center god files. Future decomposition can move one mapped slice at a time with snapshot guards instead of guessing hidden contracts from file length alone.
## ADR-105 - writer_agent lifecycle spine moves to a dedicated mixin before `_call_llm`, while module monkeypatch surface stays stable

Status: accepted

Date: 2026-07-10

Delivery: PRD-047.42-APPLY-5 implementation completed in workspace; delivery metadata pending follow-up commit sync.

Context: PRD-047.42-APPLY-4 already removed the self-bound fallback/state cluster from `writer_agent.py`, leaving the next smallest mapped slice as the lifecycle spine: `_resolve_runtime_settings()` and the public `write()` entrypoint. This slice is riskier than previous ones because `write()` is the only public answer-generation door of `WriterAgent`, owns the safety-active fallback branch, and calls `_call_llm`, `_enforce_answer_compliance`, and the already extracted fallback helpers. At the same time, accepted contract tests still monkeypatch `bot_agent.multiagent.agents.writer_agent.get_temperature_for_agent`, so a naive move could preserve behavior but still break the established test/compat surface.

Decision:
- move `_resolve_runtime_settings()` and `write()` into a dedicated `WriterAgentLifecycleMixin`;
- make `WriterAgent` inherit in explicit order: `WriterAgent(WriterAgentLifecycleMixin, WriterAgentFallbackStateMixin)`;
- keep `__init__` and `_resolve_model()` in the main class;
- preserve the old module monkeypatch surface by adding a thin `WriterAgent._get_temperature_for_agent()` wrapper, and let the moved runtime-settings method call that wrapper through `self`;
- prove behavior with four before/after write-path snapshots: safety success, safety exception, normal empty result, and normal exception;
- keep `_call_llm`, `_enforce_answer_compliance`, `_enforce_mvp_free_dialogue_compliance`, `writer_contract.py`, and all admin decomposition files out of scope.

Consequences: the public lifecycle entrypoint is now outside the main god-file without changing answer behavior or breaking accepted monkeypatch-based contract tests. The next decomposition step should target `_call_llm` as its own sub-series rather than trying to combine it with compliance or contract-prompt assembly.

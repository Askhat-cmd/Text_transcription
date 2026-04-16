"""Compatibility facade for routing stage helper modules (Wave 147)."""

from __future__ import annotations

from .routing_context_helpers import (
    INFORMATIONAL_MODE_PROMPT,
    _apply_fast_path_debug_bootstrap,
    _attach_routing_stage_debug_trace,
    _build_fast_path_mode_directive,
    _build_phase8_context_suffix,
    _build_state_context_mode_prompt,
    _finalize_routing_context_and_trace,
    _resolve_practice_selection_context,
    _resolve_routing_and_apply_block_cap,
)
from .routing_pre_stage_helpers import (
    _build_contradiction_payload,
    _compute_diagnostics_v1,
    _resolve_pre_routing,
    _run_state_analysis_stage,
    _run_state_and_pre_routing_pipeline,
)

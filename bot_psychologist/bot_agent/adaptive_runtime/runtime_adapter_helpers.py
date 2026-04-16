"""Runtime adapter factories extracted from runtime_misc_helpers (Wave 129)."""

from __future__ import annotations


def _build_output_validation_policy_adapter(
    *,
    apply_output_validation_policy,
    validator,
    force_enabled: bool,
):
    def _adapter(
        *,
        answer: str,
        query: str = "",
        route: str,
        mode: str,
        generate_retry=None,
    ):
        return apply_output_validation_policy(
            answer=answer,
            query=query,
            route=route,
            mode=mode,
            validator=validator,
            force_enabled=force_enabled,
            generate_retry=generate_retry,
        )

    return _adapter


def _build_runtime_output_validation_policy_adapter(*, force_enabled: bool):
    from ..output_validator import output_validator as _runtime_output_validator
    from .mode_policy_helpers import (
        _apply_output_validation_policy as _runtime_apply_output_validation_policy,
    )

    return _build_output_validation_policy_adapter(
        apply_output_validation_policy=_runtime_apply_output_validation_policy,
        validator=_runtime_output_validator,
        force_enabled=force_enabled,
    )


def _build_set_working_state_best_effort_adapter(
    *,
    set_working_state_best_effort,
    build_working_state,
    logger,
):
    return lambda **kwargs: set_working_state_best_effort(
        build_working_state=build_working_state,
        logger=logger,
        **kwargs,
    )

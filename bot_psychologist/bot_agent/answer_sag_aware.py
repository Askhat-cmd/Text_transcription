"""Legacy stub: SAG-aware pipeline retired in Neo runtime (PRD 11.0).

Full legacy implementation archived at `bot_agent/legacy/python/answer_sag_aware.py`.
"""

from __future__ import annotations


def answer_question_sag_aware(*_args, **_kwargs):
    raise RuntimeError(
        "Legacy pipeline 'answer_question_sag_aware' is archived and disabled in Neo runtime. "
        "Use /api/v1/questions/adaptive instead."
    )


def ask_sag(*args, **kwargs):
    return answer_question_sag_aware(*args, **kwargs)

"""Legacy stub: basic pipeline retired in Neo runtime (PRD 11.0).

Full legacy implementation archived at `bot_agent/legacy/python/answer_basic.py`.
"""

from __future__ import annotations


def answer_question_basic(*_args, **_kwargs):
    raise RuntimeError(
        "Legacy pipeline 'answer_question_basic' is archived and disabled in Neo runtime. "
        "Use /api/v1/questions/adaptive instead."
    )


def ask(*args, **kwargs):
    return answer_question_basic(*args, **kwargs)

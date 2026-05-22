from __future__ import annotations

from pathlib import Path
import sys

CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[2]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))
import json
from pathlib import Path

from bot_agent.multiagent import creator_live_evidence_rag_repair as hf1


def test_hf1_normal_user_no_effect_gate(tmp_path: Path) -> None:
    source_dir = tmp_path / "TO_DO_LIST" / "logs" / "PRD-046.1.35"
    source_dir.mkdir(parents=True)
    (source_dir / "normal_user_boundary_proof.json").write_text(
        json.dumps(
            {
                "normal_user_apply_effect_count": 0,
                "normal_user_provider_call_count": 0,
                "writer_prompt_delta_count": 0,
                "final_answer_path_delta_count": 0,
                "trace_private_leak_count": 0,
            }
        ),
        encoding="utf-8",
    )

    payload = hf1.build_normal_user_no_effect_gate(source_root=tmp_path)
    assert payload["normal_user_no_effect_gate_passed"] is True
    assert payload["normal_user_activation_allowed"] is False
    assert payload["all_users_mode_enabled"] is False


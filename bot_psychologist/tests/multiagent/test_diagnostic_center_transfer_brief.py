from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_stabilization_cleanup as runner


REQUIRED_SECTIONS = [
    "## 1. Текущее состояние проекта",
    "## 2. Что завершено в Diagnostic Center / Prompt-Constraint Pilot цепочке",
    "## 3. Ключевые инварианты",
    "## 4. Runtime architecture",
    "## 5. Knowledge Base state",
    "## 6. Что нельзя делать",
    "## 7. Какие gates обязательны",
    "## 8. Что осталось сделать дальше",
    "## 9. Рекомендуемый следующий PRD",
    "## 10. Короткий промт для нового чата",
]


def test_transfer_brief_created_with_required_sections(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    reports_dir = tmp_path / "reports"
    runner.run(
        argparse.Namespace(source_dir="TO_DO_LIST/logs/PRD-046.1.14", repo_root=".", output_dir=str(out_dir), reports_dir=str(reports_dir), strict=True)
    )
    brief = reports_dir / "PRD-046.1.15_TRANSFER_BRIEF_TO_NEW_CHAT.md"
    assert brief.exists()
    text = brief.read_text(encoding="utf-8")
    for section in REQUIRED_SECTIONS:
        assert section in text

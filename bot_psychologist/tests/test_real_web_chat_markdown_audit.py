from __future__ import annotations

from scripts.run_prd_047_11_audit import run_web_chat_markdown_audit


def test_markdown_audit_writes_real_chat_artifacts(tmp_path) -> None:
    payload = run_web_chat_markdown_audit(
        chat_url="http://127.0.0.1:3000/chat",
        log_dir=tmp_path,
    )
    assert payload.get("status") in {"passed", "warning"}
    assert (tmp_path / "markdown_real_chat_result.json").exists()

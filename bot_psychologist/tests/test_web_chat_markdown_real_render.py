from __future__ import annotations

from scripts.run_prd_047_11_writer_first_eval import run_web_chat_markdown_real_smoke


def test_web_chat_markdown_real_smoke_writes_artifacts(tmp_path) -> None:
    payload = run_web_chat_markdown_real_smoke(
        chat_url="http://127.0.0.1:5173/chat",
        log_dir=tmp_path,
    )
    assert payload.get("status") in {"passed", "warning"}
    assert (tmp_path / "web_chat_markdown_real_smoke.json").exists()
    assert (tmp_path / "web_chat_markdown_real_smoke.html").exists()


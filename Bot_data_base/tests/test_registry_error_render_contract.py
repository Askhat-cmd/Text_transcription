from __future__ import annotations

from api.routes import registry


def test_registry_error_render_contract_static() -> None:
    html = (registry._repo_root() / "Bot_data_base" / "web_ui" / "registry.html").read_text(encoding="utf-8")
    js = (registry._repo_root() / "Bot_data_base" / "web_ui" / "static" / "registry.js").read_text(encoding="utf-8")

    assert "id=\"registry-errors\"" in html
    assert "Загрузка реестра..." in html or "Загрузка реестра..." in js
    assert "Ошибка загрузки реестра:" in js
    assert "Источники не найдены" in js
    assert "loadRegistry" in js

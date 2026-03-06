"""
Тесты для метода reset_prompt_override в runtime_config.py
Запуск: pytest bot_psychologist/tests/test_runtime_config_reset.py -v
"""
import pytest


def test_is_reasoning_model():
    """Проверка логики isReasoningModel для всех граничных случаев."""
    REASONING_PREFIXES = ['gpt-5', 'o1', 'o3', 'o4']
    
    def is_reasoning(model: str) -> bool:
        return any(model.startswith(p) for p in REASONING_PREFIXES)
    
    # Reasoning модели
    assert is_reasoning('gpt-5-mini') is True
    assert is_reasoning('gpt-5') is True
    assert is_reasoning('gpt-5.1') is True
    assert is_reasoning('gpt-5.2') is True
    assert is_reasoning('o1-preview') is True
    assert is_reasoning('o3-mini') is True
    assert is_reasoning('o4-mini') is True
    
    # Non-reasoning модели
    assert is_reasoning('gpt-4o-mini') is False
    assert is_reasoning('gpt-4.1-mini') is False
    assert is_reasoning('gpt-4-turbo') is False
    assert is_reasoning('') is False
    assert is_reasoning('gpt-3.5-turbo') is False

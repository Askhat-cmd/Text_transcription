from bot_agent.config import config
from bot_agent.retrieval.confidence_scorer import ConfidenceScorer


class TestConfidenceCap:
    @staticmethod
    def make_blocks(n: int):
        return [("b", 0.9 - i * 0.01) for i in range(n)]

    def test_medium_level_returns_5_blocks(self, monkeypatch):
        monkeypatch.setattr(config, "CONFIDENCE_CAP_MEDIUM", 5, raising=False)
        scorer = ConfidenceScorer()
        result = scorer.suggest_block_cap(9, "medium")
        assert result == 5

    def test_high_level_returns_7_blocks(self, monkeypatch):
        monkeypatch.setattr(config, "CONFIDENCE_CAP_HIGH", 7, raising=False)
        scorer = ConfidenceScorer()
        result = scorer.suggest_block_cap(9, "high")
        assert result == 7

    def test_low_level_returns_3_blocks(self, monkeypatch):
        monkeypatch.setattr(config, "CONFIDENCE_CAP_LOW", 3, raising=False)
        scorer = ConfidenceScorer()
        result = scorer.suggest_block_cap(9, "low")
        assert result == 3

    def test_zero_level_returns_0_blocks(self, monkeypatch):
        monkeypatch.setattr(config, "CONFIDENCE_CAP_ZERO", 0, raising=False)
        scorer = ConfidenceScorer()
        result = scorer.suggest_block_cap(5, "zero")
        assert result == 0

    def test_cap_does_not_expand_blocks(self, monkeypatch):
        monkeypatch.setattr(config, "CONFIDENCE_CAP_HIGH", 7, raising=False)
        scorer = ConfidenceScorer()
        result = scorer.suggest_block_cap(3, "high")
        assert result == 3

    def test_cap_configurable_via_runtime_override(self, monkeypatch):
        monkeypatch.setattr(config, "CONFIDENCE_CAP_MEDIUM", 6, raising=False)
        scorer = ConfidenceScorer()
        result = scorer.suggest_block_cap(9, "medium")
        assert result == 6

    def test_cap_log_message_format(self, caplog, monkeypatch):
        monkeypatch.setattr(config, "CONFIDENCE_CAP_MEDIUM", 5, raising=False)
        scorer = ConfidenceScorer()
        scorer.suggest_block_cap(9, "medium")
        assert any(
            "cap applied" in r.message and "level=medium" in r.message
            for r in caplog.records
        )


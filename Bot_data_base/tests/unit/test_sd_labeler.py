import json
from unittest.mock import patch

from models.universal_block import UniversalBlock
from processors.sd_labeler import SDLabeler


def test_sd_labeler_assigns_level():
    labeler = SDLabeler(config={})
    blocks = [UniversalBlock(text="Я чувствую тревогу и хочу поддержки")]
    with patch.object(
        SDLabeler,
        "_call_openai",
        return_value='{"sd_level":"GREEN","sd_secondary":"","sd_confidence":0.8,"complexity":0.4,"reasoning":"test"}',
    ):
        result = labeler.label_blocks(blocks)
    assert result[0].sd_level == "GREEN"
    assert result[0].sd_confidence == 0.8


def test_low_confidence_marked_uncertain():
    labeler = SDLabeler(config={"min_confidence": 0.5})
    blocks = [UniversalBlock(text="Непонятный текст")]
    with patch.object(
        SDLabeler,
        "_call_openai",
        return_value='{"sd_level":"BLUE","sd_secondary":"","sd_confidence":0.3,"complexity":0.5,"reasoning":"unclear"}',
    ):
        result = labeler.label_blocks(blocks)
    assert result[0].sd_level == "UNCERTAIN"


def test_batch_processing():
    labeler = SDLabeler(config={"batch_size": 5})
    blocks = [UniversalBlock(text=f"Текст {i}") for i in range(10)]

    batch_response = json.dumps(
        [
            {
                "sd_level": "GREEN",
                "sd_secondary": "",
                "sd_confidence": 0.9,
                "complexity": 0.4,
                "reasoning": "ok",
            }
            for _ in range(5)
        ]
    )

    with patch.object(
        SDLabeler,
        "_call_openai",
        side_effect=[batch_response, batch_response],
    ) as mock_call:
        result = labeler.label_blocks(blocks)

    assert mock_call.call_count == 2
    assert len(result) == 10

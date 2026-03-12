"""
SD Labeler — автоматическая SD-разметка чанков через LLM.
Адаптирован под UniversalBlock.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from dotenv import load_dotenv
from openai import OpenAI

from models.universal_block import UniversalBlock

load_dotenv()

logger = logging.getLogger(__name__)


SD_LABELER_SYSTEM_PROMPT = """
Ты эксперт по Спиральной Динамике Клэра Грейвза.
Твоя задача — определить уровень сознания, который отражает данный текстовый блок.

УРОВНИ (выбери ОДИН основной):
- BEIGE: выживание, базовые инстинкты, физические потребности
- PURPLE: традиции, семья, магическое мышление, коллектив, судьба
- RED: сила, эго, немедленный результат, власть, "я хочу"
- BLUE: порядок, долг, правила, дисциплина, иерархия, вина, должен
- ORANGE: успех, логика, достижения, эффективность, результат, стратегия
- GREEN: чувства, эмпатия, принятие, равенство, гармония, "я чувствую"
- YELLOW: системность, паттерны, интеграция, мета-наблюдение, контекст
- TURQUOISE: единство, трансцендентность, целостность бытия, планетарное

Также оцени сложность текста:
- complexity 0.0-0.3: простой
- complexity 0.4-0.6: средний
- complexity 0.7-1.0: сложный

Верни JSON:
{
  "sd_level": "GREEN",
  "sd_secondary": "YELLOW",
  "sd_confidence": 0.85,
  "complexity": 0.45,
  "reasoning": "Краткое объяснение"
}

Если передан массив текстов, верни JSON МАССИВ объектов
того же размера, в том же порядке:
[{...}, {...}, {...}]
"""


class SDLabeler:
    """Автоматическая SD-разметка UniversalBlock через LLM."""

    def __init__(self, config: dict | None = None) -> None:
        cfg = self._extract_sd_config(config or {})
        self._client = None
        self.model = cfg.get("model", "gpt-4o-mini")
        self.temperature = float(cfg.get("temperature", 0.1))
        self.max_tokens = int(cfg.get("max_tokens", 300))
        self.max_chars = int(cfg.get("max_chars", 1500))
        self.min_confidence = float(cfg.get("min_confidence", 0.5))
        self.batch_size = int(cfg.get("batch_size", 5))

    def label_blocks(self, blocks: List[UniversalBlock]) -> List[UniversalBlock]:
        if not blocks:
            return []

        results: List[UniversalBlock] = []
        for i in range(0, len(blocks), self.batch_size):
            batch = blocks[i : i + self.batch_size]
            labeled = self._label_batch(batch)
            results.extend(labeled)
        return results

    def _label_batch(self, blocks: List[UniversalBlock]) -> List[UniversalBlock]:
        texts = [b.text or "" for b in blocks]
        response_text = self._call_with_retries(texts)
        labels = self._parse_response(response_text, len(blocks))

        labeled_blocks: List[UniversalBlock] = []
        for block, label in zip(blocks, labels):
            sd_level = label.get("sd_level", "GREEN")
            sd_confidence = float(label.get("sd_confidence", 0.0))
            sd_secondary = label.get("sd_secondary", "") or ""
            complexity = float(label.get("complexity", 0.5))

            if sd_confidence < self.min_confidence:
                logger.warning(
                    f"[SD_LABELER] low confidence {sd_confidence:.2f} for block {block.block_id}"
                )
                sd_level = "UNCERTAIN"

            block.sd_level = sd_level
            block.sd_confidence = sd_confidence
            block.sd_secondary = sd_secondary
            block.complexity = complexity
            labeled_blocks.append(block)

        return labeled_blocks

    def _call_with_retries(self, texts: List[str]) -> str:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                return self._call_openai(texts)
            except Exception as exc:
                last_error = exc
                logger.error(f"[SD_LABELER] API error attempt {attempt + 1}/3: {exc}")
        logger.error(f"[SD_LABELER] giving up after retries: {last_error}")
        return json.dumps([self._default_label() for _ in texts])

    def _call_openai(self, texts: List[str]) -> str:
        items = [
            {"id": i, "text": (t or "")[: self.max_chars]}
            for i, t in enumerate(texts)
        ]
        user_content = (
            "Тексты для анализа (JSON массив объектов):\n"
            + json.dumps(items, ensure_ascii=False)
        )

        client = self._get_client()
        response = client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            messages=[
                {"role": "system", "content": SD_LABELER_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
        )
        raw = (response.choices[0].message.content or "").strip()
        logger.debug(f"[SD_LABELER] raw response: {raw[:200]}")
        return raw

    def _parse_response(self, raw: str, expected_len: int) -> List[Dict[str, Any]]:
        try:
            data = json.loads(raw)
        except Exception as exc:
            logger.warning(f"[SD_LABELER] JSON parse error: {exc}")
            return [self._default_label() for _ in range(expected_len)]

        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list):
            return [self._default_label() for _ in range(expected_len)]

        if len(data) != expected_len:
            logger.warning(
                f"[SD_LABELER] response size mismatch: {len(data)} != {expected_len}"
            )
            return [self._default_label() for _ in range(expected_len)]

        return data

    def _get_client(self) -> OpenAI:
        if self._client is None:
            import os

            self._client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        return self._client

    @staticmethod
    def _default_label() -> Dict[str, Any]:
        return {
            "sd_level": "GREEN",
            "sd_secondary": "",
            "sd_confidence": 0.0,
            "complexity": 0.5,
            "reasoning": "default fallback on error",
        }

    @staticmethod
    def _extract_sd_config(config: dict) -> dict:
        if "sd_labeling" in config and isinstance(config.get("sd_labeling"), dict):
            return config["sd_labeling"]
        return config

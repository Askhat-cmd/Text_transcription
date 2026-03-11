from __future__ import annotations

import os
from typing import Tuple


class BookIngestor:
    """
    Принимает загруженный файл (.txt или .md).
    Валидирует, определяет кодировку, возвращает текст.
    """

    SUPPORTED_FORMATS = {".txt", ".md"}

    def validate_file(self, file_path: str) -> Tuple[bool, str]:
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.SUPPORTED_FORMATS:
            return False, f"Unsupported format: {ext}"
        if not os.path.exists(file_path):
            return False, "File not found"
        return True, ""

    def detect_encoding(self, file_path: str) -> str:
        with open(file_path, "rb") as f:
            data = f.read()
        for enc in ("utf-8", "cp1251", "latin-1"):
            try:
                data.decode(enc)
                return enc
            except UnicodeDecodeError:
                continue
        return "latin-1"

    def load_text(self, file_path: str) -> str:
        encoding = self.detect_encoding(file_path)
        with open(file_path, "r", encoding=encoding, errors="ignore") as f:
            text = f.read()
        return text.strip()

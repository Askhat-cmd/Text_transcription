"""Unit tests for embedding provider abstraction."""

from __future__ import annotations

import sys
import types

import numpy as np
import pytest

from bot_agent.embedding_provider import (
    E5EmbeddingProvider,
    SentenceTransformerEmbeddingProvider,
    create_embedding_provider,
)


class _FakeSentenceTransformer:
    last_encode_input = None

    def __init__(self, model_name: str, device: str = "cpu") -> None:
        self.model_name = model_name
        self.device = device

    def encode(self, inputs, **_kwargs):
        _FakeSentenceTransformer.last_encode_input = inputs
        if isinstance(inputs, list):
            return np.array([[0.1, 0.2, 0.3] for _ in inputs], dtype=np.float32)
        return np.array([0.1, 0.2, 0.3], dtype=np.float32)


def _install_fake_ml_modules(monkeypatch: pytest.MonkeyPatch, gpu: bool = False) -> None:
    st_mod = types.ModuleType("sentence_transformers")
    st_mod.SentenceTransformer = _FakeSentenceTransformer

    torch_mod = types.ModuleType("torch")
    torch_mod.cuda = types.SimpleNamespace(is_available=lambda: gpu)
    torch_mod.backends = types.SimpleNamespace(
        mps=types.SimpleNamespace(is_available=lambda: False)
    )

    monkeypatch.setitem(sys.modules, "sentence_transformers", st_mod)
    monkeypatch.setitem(sys.modules, "torch", torch_mod)


def test_e5_provider_applies_query_and_passage_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_ml_modules(monkeypatch, gpu=False)
    provider = E5EmbeddingProvider(model_name="intfloat/multilingual-e5-base", device="cpu")

    query_vec = provider.embed_query("hello")
    assert isinstance(query_vec, list)
    assert _FakeSentenceTransformer.last_encode_input == "query: hello"

    passage_vecs = provider.embed_passages(["a", "b"])
    assert isinstance(passage_vecs, list)
    assert len(passage_vecs) == 2
    assert _FakeSentenceTransformer.last_encode_input == ["passage: a", "passage: b"]


def test_factory_selects_provider_by_model_name(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_ml_modules(monkeypatch, gpu=False)

    e5 = create_embedding_provider("intfloat/multilingual-e5-base", device="cpu")
    assert isinstance(e5, E5EmbeddingProvider)

    legacy = create_embedding_provider("paraphrase-multilingual-MiniLM-L12-v2", device="cpu")
    assert isinstance(legacy, SentenceTransformerEmbeddingProvider)


def test_e5_large_requires_gpu_unless_cpu_device(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_ml_modules(monkeypatch, gpu=False)

    with pytest.raises(RuntimeError):
        E5EmbeddingProvider(model_name="intfloat/multilingual-e5-large", device="auto")

    provider = E5EmbeddingProvider(model_name="intfloat/multilingual-e5-large", device="cpu")
    assert provider.model_name().endswith("e5-large")


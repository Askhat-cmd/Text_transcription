import json
from pathlib import Path

import pipeline_runner
from storage import chroma_manager as chroma_manager_module
from storage.chroma_manager import ChromaManager
from tools import chroma_recovery


class _FakeCollection:
    def __init__(self):
        self._count = 0

    def add(self, ids, embeddings, documents, metadatas):  # noqa: ARG002
        self._count += len(ids)

    def count(self):
        return self._count

    def get(self, *args, **kwargs):  # noqa: ARG002
        return {"ids": [], "embeddings": []}

    def delete(self, *args, **kwargs):  # noqa: ARG002
        return None

    @property
    def metadata(self):
        return {"dimension": 3}


class _FakeClient:
    def __init__(self):
        self.collection = _FakeCollection()

    def get_or_create_collection(self, name):  # noqa: ARG002
        return self.collection

    def list_collections(self):
        class C:
            name = "test_col"

        return [C()]

    def delete_collection(self, name):  # noqa: ARG002
        self.collection = _FakeCollection()


def test_chroma_manager_uses_explicit_embedding_model(monkeypatch) -> None:
    captured = {}

    class FakeSentenceTransformer:
        def __init__(self, model_name):
            captured["model_name"] = model_name

        def encode(self, texts, convert_to_numpy=True):  # noqa: ARG002
            return [[0.0, 0.0, 0.0] for _ in texts]

    fake_client = _FakeClient()
    monkeypatch.setattr(chroma_manager_module.chromadb, "EphemeralClient", lambda settings: fake_client)  # noqa: ARG005
    monkeypatch.setattr(chroma_manager_module, "SentenceTransformer", FakeSentenceTransformer)
    monkeypatch.delenv("BOT_DB_DISABLE_EMBEDDINGS", raising=False)

    manager = ChromaManager(":memory:", "test_col", embedding_model_name="intfloat/multilingual-e5-large")
    assert manager.embedding_model_name == "intfloat/multilingual-e5-large"
    assert captured["model_name"] == "intfloat/multilingual-e5-large"


def test_chroma_manager_env_fallback_when_model_missing(monkeypatch) -> None:
    captured = {}

    class FakeSentenceTransformer:
        def __init__(self, model_name):
            captured["model_name"] = model_name

        def encode(self, texts, convert_to_numpy=True):  # noqa: ARG002
            return [[0.0, 0.0, 0.0] for _ in texts]

    fake_client = _FakeClient()
    monkeypatch.setattr(chroma_manager_module.chromadb, "EphemeralClient", lambda settings: fake_client)  # noqa: ARG005
    monkeypatch.setattr(chroma_manager_module, "SentenceTransformer", FakeSentenceTransformer)
    monkeypatch.delenv("BOT_DB_DISABLE_EMBEDDINGS", raising=False)
    monkeypatch.setenv("SENTENCE_TRANSFORMERS_MODEL", "env/fallback-model")

    manager = ChromaManager(":memory:", "test_col")
    assert manager.embedding_model_name == "env/fallback-model"
    assert captured["model_name"] == "env/fallback-model"


def test_pipeline_runner_passes_embedding_model_to_chroma_manager(tmp_path: Path, monkeypatch) -> None:
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        "\n".join(
            [
                "pipeline:",
                "  youtube:",
                "    subtitles_dir: data/uploads/subtitles",
                "    output_dir: data/processed/youtube",
                "  books:",
                "    uploads_dir: data/uploads/books",
                "    output_dir: data/processed/books",
                "chunking: {}",
                "sd_labeling: {}",
                "storage:",
                "  registry_path: data/registry.json",
                "  chroma_db_path: data/chroma_db",
                "  collection_name: test_collection",
                "  json_export_dir: data/processed",
                "embedding:",
                "  model: intfloat/multilingual-e5-large",
            ]
        ),
        encoding="utf-8",
    )

    captured = {}

    class FakeChromaManager:
        def __init__(self, db_path, collection_name, embedding_model_name=None):
            captured["db_path"] = db_path
            captured["collection_name"] = collection_name
            captured["embedding_model_name"] = embedding_model_name
            self._model = object()

    class _Dummy:
        def __init__(self, *args, **kwargs):  # noqa: ARG002
            pass

    monkeypatch.setattr(pipeline_runner, "ChromaManager", FakeChromaManager)
    monkeypatch.setattr(pipeline_runner, "SourceRegistry", _Dummy)
    monkeypatch.setattr(pipeline_runner, "JSONExporter", _Dummy)
    monkeypatch.setattr(pipeline_runner, "YouTubeIngestor", _Dummy)
    monkeypatch.setattr(pipeline_runner, "BookIngestor", _Dummy)
    monkeypatch.setattr(pipeline_runner, "SemanticChunker", _Dummy)
    monkeypatch.setattr(pipeline_runner, "BookChunker", _Dummy)
    monkeypatch.setattr(pipeline_runner, "SDLabeler", _Dummy)
    monkeypatch.setattr(pipeline_runner, "BlockNormalizer", _Dummy)
    monkeypatch.setattr(pipeline_runner, "load_dotenv", lambda *args, **kwargs: None)

    _runner = pipeline_runner.PipelineRunner(config_path=str(cfg_path))
    assert _runner is not None
    assert captured["embedding_model_name"] == "intfloat/multilingual-e5-large"


def test_reset_requires_confirm(tmp_path: Path, monkeypatch) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "storage:\n  chroma_db_path: data/chroma_db\n  collection_name: test_col\nembedding:\n  model: model\n",
        encoding="utf-8",
    )
    blocks = tmp_path / "all_blocks_merged.json"
    blocks.write_text(json.dumps({"blocks": [{"id": "1", "text": "x", "source": "book:s"}]}), encoding="utf-8")

    class FakeManager:
        def __init__(self, *args, **kwargs):  # noqa: ARG002
            self.reset_called = False
            self.add_called = False

        def probe_collection_health(self):
            return {"collection_count": 0, "dimension_mismatch": False}

        def reset_collection(self):
            self.reset_called = True

        def add_blocks(self, blocks):  # noqa: ARG002
            self.add_called = True
            return 1

    fake_manager = FakeManager()
    monkeypatch.setattr(chroma_recovery, "ChromaManager", lambda *args, **kwargs: fake_manager)
    monkeypatch.setattr(
        chroma_recovery,
        "probe_chroma_readiness",
        lambda **kwargs: {"api_query": {"status_code": 503}, "api_status": {"status_code": 200}},
    )
    monkeypatch.setattr(
        chroma_recovery,
        "run_retrieval_probe_snapshot",
        lambda **kwargs: {"queries": []},
    )

    result = chroma_recovery.run_recovery(
        config_path=cfg,
        output_dir=tmp_path / "out",
        report_prefix="PRD-046.0.4.3",
        api_base_url="http://127.0.0.1:8003",
        blocks_path=blocks,
        probe_only=False,
        dry_run=False,
        do_reset=True,
        do_reindex=False,
        confirm=False,
    )
    assert result["mutation_blocked"] is True
    assert fake_manager.reset_called is False


def test_reindex_dry_run_does_not_mutate(tmp_path: Path, monkeypatch) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "storage:\n  chroma_db_path: data/chroma_db\n  collection_name: test_col\nembedding:\n  model: model\n",
        encoding="utf-8",
    )
    blocks = tmp_path / "all_blocks_merged.json"
    blocks.write_text(
        json.dumps(
            {
                "blocks": [
                    {
                        "id": "1",
                        "text": "SECRET_TEXT",
                        "summary": "краткое безопасное summary для governed gate",
                        "source": "book:s",
                        "metadata": {
                            "boundary_confidence": 0.9,
                            "governance": {
                                "schema_version": "governance_v1",
                                "chunk_type": "theory",
                                "allowed_use": ["writer_context"],
                                "safety_flags": ["not_for_direct_quote"],
                                "lens_family": ["shame"],
                            },
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    class FakeManager:
        def __init__(self, *args, **kwargs):  # noqa: ARG002
            self.reset_called = False
            self.add_called = False

        def probe_collection_health(self):
            return {"collection_count": 0, "dimension_mismatch": False}

        def reset_collection(self):
            self.reset_called = True

        def add_blocks(self, blocks):  # noqa: ARG002
            self.add_called = True
            return 1

    fake_manager = FakeManager()
    monkeypatch.setattr(chroma_recovery, "ChromaManager", lambda *args, **kwargs: fake_manager)
    monkeypatch.setattr(
        chroma_recovery,
        "probe_chroma_readiness",
        lambda **kwargs: {"api_query": {"status_code": 200}, "api_status": {"status_code": 200}},
    )
    monkeypatch.setattr(
        chroma_recovery,
        "run_retrieval_probe_snapshot",
        lambda **kwargs: {"queries": []},
    )

    out_dir = tmp_path / "out"
    result = chroma_recovery.run_recovery(
        config_path=cfg,
        output_dir=out_dir,
        report_prefix="PRD-046.0.4.3",
        api_base_url="http://127.0.0.1:8003",
        blocks_path=blocks,
        probe_only=False,
        dry_run=True,
        do_reset=True,
        do_reindex=True,
        confirm=True,
    )
    assert result["mutation_blocked"] is False
    assert fake_manager.reset_called is False
    assert fake_manager.add_called is False

    probe_content = (out_dir / "chroma_recovery_probe.json").read_text(encoding="utf-8")
    assert "SECRET_TEXT" not in probe_content


def test_gate_block_prevents_mutation_even_with_confirm(tmp_path: Path, monkeypatch) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "storage:\n  chroma_db_path: data/chroma_db\n  collection_name: test_col\nembedding:\n  model: model\n",
        encoding="utf-8",
    )
    blocks = tmp_path / "all_blocks_merged.json"
    blocks.write_text(
        json.dumps({"blocks": [{"id": "1", "text": "x", "summary": "", "source": "book:s"}]}),
        encoding="utf-8",
    )

    class FakeManager:
        def __init__(self, *args, **kwargs):  # noqa: ARG002
            self.reset_called = False
            self.add_called = False

        def probe_collection_health(self):
            return {"collection_count": 0, "dimension_mismatch": False}

        def reset_collection(self):
            self.reset_called = True

        def add_blocks(self, blocks):  # noqa: ARG002
            self.add_called = True
            return 1

    fake_manager = FakeManager()
    monkeypatch.setattr(chroma_recovery, "ChromaManager", lambda *args, **kwargs: fake_manager)
    monkeypatch.setattr(
        chroma_recovery,
        "probe_chroma_readiness",
        lambda **kwargs: {"api_query": {"status_code": 503}, "api_status": {"status_code": 200}},
    )
    monkeypatch.setattr(
        chroma_recovery,
        "run_retrieval_probe_snapshot",
        lambda **kwargs: {"queries": []},
    )

    result = chroma_recovery.run_recovery(
        config_path=cfg,
        output_dir=tmp_path / "out",
        report_prefix="PRD-046.0.4.3",
        api_base_url="http://127.0.0.1:8003",
        blocks_path=blocks,
        probe_only=False,
        dry_run=False,
        do_reset=True,
        do_reindex=True,
        confirm=True,
    )
    assert result["mutation_blocked"] is True
    assert result["reindex_allowed"] is False
    assert fake_manager.reset_called is False
    assert fake_manager.add_called is False


def test_write_reports_uses_report_prefix(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    report_prefix = "PRD-046.0.4.3"
    result = {
        "reindex_allowed": True,
        "local_blocks_count": 2,
        "indexed_blocks_count": 2,
        "collection_count_before": 0,
        "collection_count_after": 2,
        "gate_status_after": "ready",
        "recommended_next_prd": "PRD-046.0.5",
    }
    recovery_probe = {
        "mode": {
            "probe_only": False,
            "dry_run": False,
            "reset": True,
            "reindex_from_json": True,
            "confirm": True,
        },
        "mutation_blocked": False,
        "mutation_reason": "",
        "reindex_allowed": True,
        "preflight_reason": "gate_passed",
        "before_health": {"collection_count": 0, "dimension_mismatch": False},
        "after_health": {"collection_count": 2, "dimension_mismatch": False},
        "audit_probe": {"api_status": {"status_code": 200}, "api_query": {"status_code": 200}},
        "local_blocks_count": 2,
        "indexed_blocks_count": 2,
    }
    gate_data = {
        "after": {
            "status": "ready",
            "blocker_reasons": [],
            "warnings": [],
            "metrics": {"total_blocks": 2},
            "recommended_next_prd": "PRD-046.0.5",
        }
    }

    chroma_recovery.write_reports(
        reports_dir=reports_dir,
        report_prefix=report_prefix,
        result=result,
        recovery_probe=recovery_probe,
        gate_data=gate_data,
    )

    assert (reports_dir / "PRD-046.0.4.3_CHROMA_REINDEX_REPORT.md").exists()
    assert (reports_dir / "PRD-046.0.4.3_GOVERNED_INDEX_GATE_REPORT.md").exists()
    assert (reports_dir / "PRD-046.0.4.3_IMPLEMENTATION_REPORT.md").exists()
    assert not (reports_dir / "PRD-046.0.4.1_CHROMA_RECOVERY_REPORT.md").exists()

import importlib
import sys
import types
from importlib.machinery import ModuleSpec


try:
    importlib.import_module("yt_dlp")
except Exception:
    yt_dlp_stub = types.ModuleType("yt_dlp")
    yt_dlp_stub.__spec__ = ModuleSpec(name="yt_dlp", loader=None)

    class DummyYoutubeDL:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def extract_info(self, *args, **kwargs):
            return {}

    yt_dlp_stub.YoutubeDL = DummyYoutubeDL
    sys.modules["yt_dlp"] = yt_dlp_stub


try:
    importlib.import_module("tiktoken")
except Exception:
    tiktoken_stub = types.ModuleType("tiktoken")
    tiktoken_stub.__spec__ = ModuleSpec(name="tiktoken", loader=None)

    class DummyEncoding:
        def encode(self, text, *args, **kwargs):  # noqa: ARG002
            if not text:
                return []
            return str(text).split()

    def encoding_for_model(_model_name: str):  # noqa: ARG001
        return DummyEncoding()

    def get_encoding(_encoding_name: str):  # noqa: ARG001
        return DummyEncoding()

    tiktoken_stub.encoding_for_model = encoding_for_model
    tiktoken_stub.get_encoding = get_encoding
    sys.modules["tiktoken"] = tiktoken_stub


try:
    importlib.import_module("chromadb")
except Exception:
    chroma_stub = types.ModuleType("chromadb")
    chroma_stub.__spec__ = ModuleSpec(name="chromadb", loader=None)

    class DummyCollection:
        def __init__(self, name="dummy"):
            self.name = name
            self._records = []

        def count(self):
            return len(self._records)

        def add(self, documents=None, embeddings=None, metadatas=None, ids=None, **kwargs):  # noqa: ARG002
            documents = documents or []
            metadatas = metadatas or []
            ids = ids or []
            for idx, doc in enumerate(documents):
                self._records.append(
                    {
                        "id": ids[idx] if idx < len(ids) else f"id_{len(self._records)}",
                        "document": doc,
                        "metadata": metadatas[idx] if idx < len(metadatas) else {},
                    }
                )

        def get(self, where=None, include=None, **kwargs):  # noqa: ARG002
            rows = list(self._records)
            if isinstance(where, dict):
                source_where = where.get("source_id")
                if isinstance(source_where, dict) and "$eq" in source_where:
                    expected = source_where["$eq"]
                    rows = [r for r in rows if (r.get("metadata") or {}).get("source_id") == expected]
            return {
                "ids": [r["id"] for r in rows],
                "documents": [r["document"] for r in rows],
                "metadatas": [r["metadata"] for r in rows],
            }

        def query(self, query_embeddings=None, n_results=5, where=None, include=None, **kwargs):  # noqa: ARG002
            rows = self.get(where=where).get("ids", [])
            full = self.get(where=where)
            docs = full.get("documents", [])[:n_results]
            metas = full.get("metadatas", [])[:n_results]
            ids = rows[:n_results]
            distances = [0.1 for _ in ids]
            return {"documents": [docs], "metadatas": [metas], "ids": [ids], "distances": [distances]}

        def delete(self, ids=None, where=None, **kwargs):  # noqa: ARG002
            if ids:
                ids_set = set(ids)
                self._records = [r for r in self._records if r["id"] not in ids_set]
                return
            if isinstance(where, dict):
                source_where = where.get("source_id")
                if isinstance(source_where, dict) and "$eq" in source_where:
                    expected = source_where["$eq"]
                    self._records = [
                        r for r in self._records if (r.get("metadata") or {}).get("source_id") != expected
                    ]
                    return
            self._records = []

    class DummyClient:
        def __init__(self, *args, **kwargs):  # noqa: ARG002
            self._collections = {}

        def get_or_create_collection(self, name, metadata=None):  # noqa: ARG002
            if name not in self._collections:
                self._collections[name] = DummyCollection(name=name)
            return self._collections[name]

        def list_collections(self):
            return list(self._collections.values())

        def get_collection(self, name):  # noqa: ARG002
            return self.get_or_create_collection(name)

    chroma_stub.PersistentClient = DummyClient
    chroma_stub.EphemeralClient = DummyClient
    sys.modules["chromadb"] = chroma_stub

    chroma_cfg_stub = types.ModuleType("chromadb.config")
    chroma_cfg_stub.__spec__ = ModuleSpec(name="chromadb.config", loader=None)

    class DummySettings:
        def __init__(self, *args, **kwargs):  # noqa: ARG002
            pass

    chroma_cfg_stub.Settings = DummySettings
    sys.modules["chromadb.config"] = chroma_cfg_stub

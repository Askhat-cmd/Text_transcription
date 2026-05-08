from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.db_api_client import RetrievedChunk
from bot_agent.retriever import SimpleRetriever


def test_retrieved_chunk_accepts_governance_field() -> None:
    chunk = RetrievedChunk(
        chunk_id="c1",
        content="text",
        score=0.9,
        sd_level=6,
        author_id="author",
        author_name="Author",
        source_type="book",
        youtube_url=None,
        start_time=None,
        end_time=None,
        block_title="Block",
        keywords=["k"],
        governance={"schema_version": "governance_v1", "chunk_type": "practice"},
    )
    assert chunk.governance and chunk.governance["schema_version"] == "governance_v1"


def test_retriever_chunk_to_block_preserves_governance() -> None:
    retriever = SimpleRetriever()
    chunk = RetrievedChunk(
        chunk_id="c2",
        content="text",
        score=0.8,
        sd_level=6,
        author_id="author",
        author_name="Author",
        source_type="book",
        youtube_url=None,
        start_time=None,
        end_time=None,
        block_title="Block",
        keywords=[],
        governance={"schema_version": "governance_v1", "chunk_type": "lens"},
    )

    block = retriever._chunk_to_block(chunk)
    assert block.governance.get("chunk_type") == "lens"

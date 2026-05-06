from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


def _load_runner_module():
    project_root = Path(__file__).resolve().parents[2]
    module_path = project_root / "scripts" / "run_quality_baseline.py"
    spec = importlib.util.spec_from_file_location("run_quality_baseline", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_extract_debug_summary_keeps_quality_trace() -> None:
    runner = _load_runner_module()
    response = {
        "trace": {
            "pipeline_version": "multiagent_v1",
            "quality_trace_version": "quality_trace_v1",
            "quality_trace": {
                "version": "quality_trace_v1",
                "summary_flags": ["generic_phrase_risk"],
            },
            "quality_trace_error": None,
        },
        "processing_time_seconds": 0.123,
    }

    summary, latency_ms = runner._extract_debug_summary(response, session_id="s-1")

    assert summary["quality_trace_version"] == "quality_trace_v1"
    assert summary["quality_trace"]["summary_flags"] == ["generic_phrase_risk"]
    assert summary["quality_trace_error"] is None
    assert latency_ms == 123.0

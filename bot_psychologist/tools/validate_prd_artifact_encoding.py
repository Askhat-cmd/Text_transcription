from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


TEXT_EXTENSIONS = {".txt", ".md", ".json", ".log", ".yaml", ".yml", ".csv"}
MOJIBAKE_MARKERS = ("Ð", "Ñ", "Ã", "Â", "РџС", "Гђ", "Г‘", "\u0085")
MAX_REASONABLE_TEXT_SIZE_BYTES = 5 * 1024 * 1024


@dataclass
class ValidationState:
    files_checked: int = 0
    utf8_decode_error_count: int = 0
    nul_byte_file_count: int = 0
    nul_char_file_count: int = 0
    replacement_char_warning_count: int = 0
    mojibake_warning_count: int = 0
    json_parse_error_count: int = 0
    empty_text_artifact_count: int = 0
    unexpected_debug_dir_count: int = 0
    warnings: list[str] | None = None
    blockers: list[str] | None = None

    def __post_init__(self) -> None:
        if self.warnings is None:
            self.warnings = []
        if self.blockers is None:
            self.blockers = []


def _safe_rel(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def _iter_target_files(*, logs_dir: Path, reports_dir: Path | None, prd: str) -> list[Path]:
    files: list[Path] = []
    if logs_dir.exists():
        files.extend([p for p in logs_dir.rglob("*") if p.is_file() and p.suffix.lower() in TEXT_EXTENSIONS])
    if reports_dir and reports_dir.exists():
        files.extend(
            [
                p
                for p in reports_dir.glob(f"{prd}*")
                if p.is_file() and p.suffix.lower() in TEXT_EXTENSIONS
            ]
        )
    dedup: dict[str, Path] = {}
    for file_path in files:
        dedup[str(file_path.resolve()).lower()] = file_path
    return sorted(dedup.values(), key=lambda p: str(p).lower())


def _validate_file(path: Path, *, repo_root: Path, state: ValidationState) -> None:
    raw = path.read_bytes()
    state.files_checked += 1
    rel = _safe_rel(path, repo_root)

    if len(raw) == 0:
        state.empty_text_artifact_count += 1
        state.blockers.append(f"{rel}:empty_file")
        return

    if len(raw) > MAX_REASONABLE_TEXT_SIZE_BYTES:
        state.warnings.append(f"{rel}:large_text_artifact_bytes={len(raw)}")

    nul_bytes = raw.count(0)
    if nul_bytes > 0:
        state.nul_byte_file_count += 1
        state.blockers.append(f"{rel}:nul_bytes={nul_bytes}")

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        state.utf8_decode_error_count += 1
        state.blockers.append(f"{rel}:utf8_decode_error:{exc.start}")
        return

    nul_chars = text.count("\x00")
    if nul_chars > 0:
        state.nul_char_file_count += 1
        state.blockers.append(f"{rel}:nul_chars={nul_chars}")

    replacement_count = text.count("�")
    if replacement_count > 0:
        state.replacement_char_warning_count += 1
        state.warnings.append(f"{rel}:replacement_chars={replacement_count}")

    if any(marker in text for marker in MOJIBAKE_MARKERS):
        state.mojibake_warning_count += 1
        state.warnings.append(f"{rel}:mojibake_marker_detected")

    if not text.strip():
        state.empty_text_artifact_count += 1
        state.blockers.append(f"{rel}:empty_text")
        return

    if path.suffix.lower() == ".json":
        try:
            json.loads(text)
        except json.JSONDecodeError as exc:
            state.json_parse_error_count += 1
            state.blockers.append(f"{rel}:json_parse_error:{exc.lineno}:{exc.colno}")


def _find_unexpected_debug_dirs(*, logs_dir: Path, prd: str) -> list[Path]:
    logs_root = logs_dir.parent if logs_dir.parent.exists() else logs_dir
    candidates = [
        logs_root / f"{prd}-debug",
        logs_root / f"{prd}_debug",
    ]
    found = [p for p in candidates if p.exists() and p.is_dir()]
    return found


def run(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()
    logs_dir = Path(args.logs_dir).resolve()
    reports_dir = Path(args.reports_dir).resolve() if args.reports_dir else None
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    state = ValidationState()
    target_files = _iter_target_files(logs_dir=logs_dir, reports_dir=reports_dir, prd=str(args.prd))
    for file_path in target_files:
        _validate_file(file_path, repo_root=repo_root, state=state)

    unexpected_debug_dirs = _find_unexpected_debug_dirs(logs_dir=logs_dir, prd=str(args.prd))
    if unexpected_debug_dirs:
        state.unexpected_debug_dir_count = len(unexpected_debug_dirs)
        for path in unexpected_debug_dirs:
            state.blockers.append(f"{_safe_rel(path, repo_root)}:unexpected_debug_dir")

    fixed_files = [str(Path(item).as_posix()) for item in (args.fixed_file or [])]
    final_status = "passed" if len(state.blockers) == 0 else "failed"

    report = {
        "schema_version": "artifact_encoding_hygiene_report_v1",
        "prd": str(args.report_prd or "PRD-046.1.2-HF1"),
        "checked_prd": str(args.prd),
        "final_status": final_status,
        "files_checked": state.files_checked,
        "utf8_decode_error_count": state.utf8_decode_error_count,
        "nul_byte_file_count": state.nul_byte_file_count,
        "nul_char_file_count": state.nul_char_file_count,
        "replacement_char_warning_count": state.replacement_char_warning_count,
        "mojibake_warning_count": state.mojibake_warning_count,
        "json_parse_error_count": state.json_parse_error_count,
        "empty_text_artifact_count": state.empty_text_artifact_count,
        "unexpected_debug_dir_count": state.unexpected_debug_dir_count,
        "fixed_files": fixed_files,
        "warnings": state.warnings,
        "blockers": state.blockers,
        "checked_files": [_safe_rel(p, repo_root) for p in target_files],
    }
    out_path = out_dir / "artifact_encoding_hygiene_report.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate PRD artifact encoding hygiene.")
    parser.add_argument("--prd", required=True, help="PRD id to validate (e.g. PRD-046.1.2).")
    parser.add_argument("--logs-dir", required=True, help="Logs directory for the checked PRD.")
    parser.add_argument("--reports-dir", default="", help="Reports directory (optional).")
    parser.add_argument("--out-dir", required=True, help="Output directory for hygiene report.")
    parser.add_argument("--report-prd", default="PRD-046.1.2-HF1", help="PRD id stored in the report.")
    parser.add_argument("--repo-root", default=".", help="Repository root path.")
    parser.add_argument(
        "--fixed-file",
        action="append",
        default=[],
        help="Fixed files list to store in report (repeatable).",
    )
    args = parser.parse_args()
    report = run(args)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["final_status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())


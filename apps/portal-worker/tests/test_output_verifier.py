"""verify_outputs: проверяет что все declared filenames есть в output_dir."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from portal_worker.runner.output_verifier import (
    OutputMissingError,
    scan_output_dir,
    verify_outputs,
)


def test_verify_passes_when_all_present(tmp_path: Path) -> None:
    (tmp_path / "report.docx").write_bytes(b"x")
    (tmp_path / "summary.json").write_bytes(b"y")
    verify_outputs(tmp_path, declared_filenames=["report.docx", "summary.json"])
    # no exception


def test_verify_raises_on_missing(tmp_path: Path) -> None:
    (tmp_path / "report.docx").write_bytes(b"x")
    with pytest.raises(OutputMissingError) as exc:
        verify_outputs(tmp_path, declared_filenames=["report.docx", "summary.json"])
    assert "summary.json" in str(exc.value)


def test_verify_passes_on_no_declared_outputs(tmp_path: Path) -> None:
    verify_outputs(tmp_path, declared_filenames=[])


def test_scan_returns_files_with_size_and_sha(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_bytes(b"hello")
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "b.txt").write_bytes(b"world")
    files = scan_output_dir(tmp_path)
    by_name = {f.relative_path: f for f in files}
    assert by_name["a.txt"].size_bytes == 5
    assert by_name["a.txt"].sha256 == hashlib.sha256(b"hello").hexdigest()
    assert by_name["subdir/b.txt"].size_bytes == 5

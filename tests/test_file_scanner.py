from pathlib import Path

from codeatlas.config import AnalysisConfig
from codeatlas.scanner import FileScanner


def test_scanner_ignores_virtual_environments(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('ok')", encoding="utf-8")
    ignored = tmp_path / ".venv"
    ignored.mkdir()
    (ignored / "ignored.py").write_text("print('ignored')", encoding="utf-8")

    result = FileScanner().scan(AnalysisConfig(repository_path=tmp_path))

    assert [path.name for path in result.python_files] == ["main.py"]


def test_scanner_respects_codeatlasignore(tmp_path: Path) -> None:
    (tmp_path / "keep.py").write_text("pass", encoding="utf-8")
    (tmp_path / "skip.py").write_text("pass", encoding="utf-8")
    (tmp_path / ".codeatlasignore").write_text("skip.py\n", encoding="utf-8")

    result = FileScanner().scan(AnalysisConfig(repository_path=tmp_path))

    assert [path.name for path in result.python_files] == ["keep.py"]

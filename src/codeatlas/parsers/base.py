"""Protocol shared by source-code parsers."""

from pathlib import Path
from typing import Protocol

from codeatlas.models import FileAnalysis


class SourceParser(Protocol):
    def parse(self, file_path: Path, repository_root: Path) -> FileAnalysis: ...

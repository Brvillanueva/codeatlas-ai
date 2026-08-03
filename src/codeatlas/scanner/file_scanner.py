"""Safe, deterministic repository scanning."""

from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path

from codeatlas.config import AnalysisConfig
from codeatlas.exceptions import InvalidRepositoryError
from codeatlas.models import AnalysisError


@dataclass(slots=True)
class ScanResult:
    files: list[Path] = field(default_factory=list)
    errors: list[AnalysisError] = field(default_factory=list)

    @property
    def python_files(self) -> list[Path]:
        return [path for path in self.files if path.suffix == ".py"]


class FileScanner:
    """Discover regular files without following symlinks or ignored paths."""

    def scan(self, config: AnalysisConfig) -> ScanResult:
        root = config.repository_path.expanduser().resolve()
        if not root.exists() or not root.is_dir():
            raise InvalidRepositoryError(
                f"Repository path does not exist or is not a directory: {root}"
            )
        patterns = self._ignore_patterns(root, config)
        result = ScanResult()
        for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().lower()):
            try:
                if path.is_symlink() or not path.is_file():
                    continue
                relative = path.relative_to(root)
                if self._should_ignore(relative, config, patterns):
                    continue
                result.files.append(path)
            except OSError as error:
                result.errors.append(
                    AnalysisError(path=str(path), message=str(error), kind="scanner_error")
                )
        return result

    def _ignore_patterns(self, root: Path, config: AnalysisConfig) -> list[str]:
        ignore = root / ".codeatlasignore"
        if not config.respect_codeatlasignore or not ignore.exists():
            return []
        try:
            return [
                line.strip().replace("\\", "/")
                for line in ignore.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            ]
        except OSError:
            return []

    def _should_ignore(self, relative: Path, config: AnalysisConfig, patterns: list[str]) -> bool:
        if (
            set(relative.parts).intersection(config.excluded_directories)
            or relative.name in config.ignored_files
        ):
            return True
        normalized = relative.as_posix()
        return any(fnmatch(normalized, pattern) or relative.match(pattern) for pattern in patterns)

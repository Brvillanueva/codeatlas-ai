"""Use case for deterministic repository analysis."""

from collections.abc import Iterable
from pathlib import Path

from codeatlas.architecture import ArchitectureAnalyzer
from codeatlas.config import AnalysisConfig
from codeatlas.dependencies import DependencyResolver
from codeatlas.graph import DependencyGraph
from codeatlas.models import AnalysisError, FileAnalysis, RepositoryAnalysis, RepositoryStats
from codeatlas.parsers import PythonAstParser
from codeatlas.scanner import FileScanner


class RepositoryAnalyzer:
    """Coordinate scanning, parsing, dependency resolution and graph metrics."""

    def __init__(
        self,
        scanner: FileScanner | None = None,
        parser: PythonAstParser | None = None,
        dependency_resolver: DependencyResolver | None = None,
    ) -> None:
        self._scanner = scanner or FileScanner()
        self._parser = parser or PythonAstParser()
        self._resolver = dependency_resolver or DependencyResolver()

    def analyze(self, repository_path: Path) -> RepositoryAnalysis:
        root = repository_path.expanduser().resolve()
        scanned = self._scanner.scan(AnalysisConfig(repository_path=root))
        files = [self._parser.parse(path, root) for path in scanned.python_files]
        dependencies, external = self._resolver.resolve(files)
        graph = DependencyGraph(files, dependencies)
        architecture = ArchitectureAnalyzer().analyze(files, dependencies)
        errors = [*scanned.errors, *self._file_errors(files)]
        return RepositoryAnalysis(
            repository_name=root.name,
            repository_path=str(root),
            files=files,
            internal_dependencies=dependencies,
            external_dependencies=external,
            central_modules=graph.central_modules(),
            architecture=architecture,
            errors=errors,
            stats=self._stats(scanned.files, files, external, errors),
        )

    def dependency_graph(self, analysis: RepositoryAnalysis) -> DependencyGraph:
        return DependencyGraph(analysis.files, analysis.internal_dependencies)

    def _file_errors(self, files: Iterable[FileAnalysis]) -> list[AnalysisError]:
        return [
            AnalysisError(path=file.path, message=file.syntax_error, kind="syntax_error")
            for file in files
            if file.syntax_error
        ]

    def _stats(
        self,
        discovered: list[Path],
        files: list[FileAnalysis],
        external: list[str],
        errors: list[AnalysisError],
    ) -> RepositoryStats:
        return RepositoryStats(
            files_discovered=len(discovered),
            python_files=len(files),
            classes=sum(len(file.classes) for file in files),
            functions=sum(len(file.functions) for file in files),
            methods=sum(len(item.methods) for file in files for item in file.classes),
            imports=sum(len(file.imports) for file in files),
            internal_imports=sum(1 for file in files for item in file.imports if item.is_internal),
            external_dependencies=len(external),
            files_with_errors=len({error.path for error in errors}),
        )

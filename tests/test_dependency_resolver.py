from pathlib import Path

from codeatlas.application import RepositoryAnalyzer
from codeatlas.dependencies import DependencyResolver
from codeatlas.models import FileAnalysis, ImportInfo

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "simple_project"


def test_resolver_detects_absolute_and_relative_internal_dependencies() -> None:
    analysis = RepositoryAnalyzer().analyze(FIXTURE_ROOT)
    edges = {(edge.source, edge.target) for edge in analysis.internal_dependencies}

    assert ("app.py", "package/service.py") in edges
    assert ("package/service.py", "package/models.py") in edges
    assert analysis.external_dependencies == []


def test_analysis_continues_when_file_has_syntax_error() -> None:
    root = Path(__file__).parent / "fixtures" / "project_with_syntax_error"
    analysis = RepositoryAnalyzer().analyze(root)

    assert analysis.stats.python_files == 1
    assert analysis.stats.files_with_errors == 1


def test_resolver_supports_a_nested_src_layout() -> None:
    files = [
        FileAnalysis(
            path="project/src/graph/state.py",
            module_name="project.src.graph.state",
        ),
        FileAnalysis(
            path="project/src/graph/builder.py",
            module_name="project.src.graph.builder",
            imports=[ImportInfo(module="src.graph.state")],
        ),
    ]

    dependencies, external = DependencyResolver().resolve(files)

    assert [(edge.source, edge.target) for edge in dependencies] == [
        ("project/src/graph/builder.py", "project/src/graph/state.py")
    ]
    assert external == []

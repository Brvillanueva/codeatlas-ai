from pathlib import Path

from codeatlas.application import RepositoryAnalyzer
from codeatlas.graph import DependencyGraph

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "simple_project"


def test_architecture_groups_files_by_detected_role() -> None:
    analysis = RepositoryAnalyzer().analyze(FIXTURE_ROOT)
    components = {component.role: component for component in analysis.architecture.components}

    assert "entrypoint" in components
    assert "service" in components
    assert "domain" in components
    assert "app.py" in components["entrypoint"].files
    assert "package/service.py" in components["service"].files
    assert "package/models.py" in components["domain"].files


def test_executive_graph_uses_components_and_hides_tests() -> None:
    analysis = RepositoryAnalyzer().analyze(FIXTURE_ROOT)
    graph = DependencyGraph(analysis.files, analysis.internal_dependencies)

    mermaid = graph.to_mermaid(view="executive", architecture=analysis.architecture)

    assert mermaid.startswith("flowchart LR")
    assert "Servicios" in mermaid
    assert "tests/test_service.py" not in mermaid


def test_technical_graph_preserves_file_imports() -> None:
    analysis = RepositoryAnalyzer().analyze(FIXTURE_ROOT)
    graph = DependencyGraph(analysis.files, analysis.internal_dependencies)

    mermaid = graph.to_mermaid(view="technical", architecture=analysis.architecture)

    assert "package/service.py" in mermaid
    assert "tests/test_service.py" in mermaid

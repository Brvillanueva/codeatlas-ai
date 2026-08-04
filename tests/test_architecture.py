from pathlib import Path

from codeatlas.application import RepositoryAnalyzer
from codeatlas.architecture import ArchitectureAnalyzer
from codeatlas.graph import DependencyGraph
from codeatlas.models import FileAnalysis, ImportInfo

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

    assert "app.py" in mermaid
    assert "package/service.py" in mermaid


def test_package_graph_aggregates_imports_and_hides_tests() -> None:
    analysis = RepositoryAnalyzer().analyze(FIXTURE_ROOT)
    graph = DependencyGraph(analysis.files, analysis.internal_dependencies)

    mermaid = graph.package_mermaid()

    assert mermaid.startswith("flowchart LR")
    assert "package" in mermaid
    assert "tests" not in mermaid


def test_file_graph_can_be_scoped_to_a_package() -> None:
    analysis = RepositoryAnalyzer().analyze(FIXTURE_ROOT)
    graph = DependencyGraph(analysis.files, analysis.internal_dependencies)

    mermaid = graph.file_mermaid(package="package")

    assert 'subgraph Selected["Area seleccionada"]' in mermaid
    assert "service.py" in mermaid
    assert "tests/test_service.py" not in mermaid


def test_class_graph_can_focus_on_one_class() -> None:
    analysis = RepositoryAnalyzer().analyze(FIXTURE_ROOT)
    graph = DependencyGraph(analysis.files, analysis.internal_dependencies)

    mermaid = graph.class_mermaid(focus="UserService")

    assert "UserService" in mermaid


def test_architecture_roles_use_path_evidence_not_imported_symbol_names() -> None:
    analysis = ArchitectureAnalyzer().analyze(
        [
            FileAnalysis(
                path="project/src/agents/create_react_agent.py",
                module_name="project.src.agents.create_react_agent",
                imports=[ImportInfo(module="src.config.configuration")],
            ),
            FileAnalysis(
                path="project/__init__.py",
                module_name="project",
            ),
        ],
        [],
    )
    components = {component.role: component for component in analysis.components}

    assert "project/src/agents/create_react_agent.py" in components["orchestration"].files
    assert "configuration" not in components
    assert "project/__init__.py" in components["unknown"].files

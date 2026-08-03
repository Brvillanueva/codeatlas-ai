"""NetworkX-backed graph representation of file dependencies."""

from typing import Literal

import networkx as nx

from codeatlas.models import ArchitectureAnalysis, DependencyEdge, FileAnalysis


class DependencyGraph:
    """Build graph metrics and Mermaid output from repository dependencies."""

    def __init__(self, files: list[FileAnalysis], edges: list[DependencyEdge]) -> None:
        self._files = files
        self._graph = nx.DiGraph()
        self._graph.add_nodes_from(file.path for file in files)
        self._graph.add_edges_from((edge.source, edge.target) for edge in edges)

    def central_modules(self, limit: int = 10) -> list[str]:
        ranked = sorted(self._graph.in_degree(), key=lambda item: (-item[1], item[0]))
        return [path for path, degree in ranked[:limit] if degree > 0]

    def to_mermaid(
        self,
        view: Literal["executive", "technical"] = "executive",
        architecture: ArchitectureAnalysis | None = None,
    ) -> str:
        """Export either a focused architecture view or the complete import graph."""
        if view == "technical":
            return self._technical_mermaid()
        return self._executive_mermaid(architecture)

    def _technical_mermaid(self) -> str:
        lines = ["graph TD"]
        nodes = sorted(self._graph.nodes())
        identifiers = {node: f"N{index}" for index, node in enumerate(nodes, start=1)}
        lines.extend(f'    {identifiers[node]}["{node}"]' for node in nodes)
        lines.extend(
            f"    {identifiers[source]} --> {identifiers[target]}"
            for source, target in sorted(self._graph.edges())
        )
        return "\n".join(lines) + "\n"

    def class_mermaid(self) -> str:
        """Export classes and inheritance only; runtime collaboration is intentionally excluded."""
        classes = [item for file in self._files for item in file.classes]
        if not classes:
            return "classDiagram\n    class Empty[\"No Python classes detected\"]\n"
        identifiers = {
            item.qualified_name: self._class_identifier(item.qualified_name, index)
            for index, item in enumerate(classes, 1)
        }
        by_name = {item.name: item.qualified_name for item in classes}
        lines = ["classDiagram"]
        for item in classes:
            identifier = identifiers[item.qualified_name]
            lines.append(f"    class {identifier} {{")
            for method in item.methods:
                lines.append(f"        +{method.name}()")
            lines.append("    }")
        for item in classes:
            for base in item.bases:
                parent = by_name.get(base.split(".")[-1])
                if parent:
                    lines.append(
                        f"    {identifiers[parent]} <|-- {identifiers[item.qualified_name]}"
                    )
        return "\n".join(lines) + "\n"

    def _class_identifier(self, qualified_name: str, index: int) -> str:
        readable = "".join(
            character if character.isalnum() else "_" for character in qualified_name
        )
        return f"{readable}_{index}"

    def _executive_mermaid(self, architecture: ArchitectureAnalysis | None) -> str:
        """Return a component-level architecture view instead of a file import listing."""
        if architecture is None or not architecture.components:
            return "flowchart LR\n    Empty[\"No architecture relations detected\"]\n"
        lines = [
            "flowchart LR",
            "    %% A --> B means: component A imports or depends on component B.",
            "    classDef entry fill:#DCEEFF,stroke:#2E74B5,stroke-width:2px,color:#1F4D78;",
            "    classDef component fill:#F8FAFC,stroke:#7A8795,color:#1F2937;",
        ]
        components = [item for item in architecture.components if item.role != "tests"]
        connected = {edge.source for edge in architecture.dependencies} | {
            edge.target for edge in architecture.dependencies
        }
        components = [
            item for item in components if item.name in connected or item.role == "entrypoint"
        ]
        if not components:
            return "flowchart LR\n    Empty[\"No connected architecture components detected\"]\n"
        identifiers = {
            component.name: f"C{index}" for index, component in enumerate(components, start=1)
        }
        for component in components:
            label = f"{component.name} ({len(component.files)} archivos)"
            lines.append(f'    {identifiers[component.name]}["{label}"]')
        for edge in architecture.dependencies:
            if edge.source in identifiers and edge.target in identifiers:
                lines.append(
                    f"    {identifiers[edge.source]} -->|{edge.imports_count} import(s)| "
                    f"{identifiers[edge.target]}"
                )
        entry_nodes = ",".join(
            identifiers[item.name] for item in components if item.role == "entrypoint"
        )
        if entry_nodes:
            lines.append(f"    class {entry_nodes} entry")
        remaining = ",".join(
            identifiers[item.name] for item in components if item.role != "entrypoint"
        )
        if remaining:
            lines.append(f"    class {remaining} component")
        return "\n".join(lines) + "\n"

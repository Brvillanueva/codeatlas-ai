"""NetworkX-backed graph representation of file dependencies."""

from typing import Literal

import networkx as nx

from codeatlas.models import ArchitectureAnalysis, ClassInfo, DependencyEdge, FileAnalysis


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

    def package_mermaid(
        self,
        include_tests: bool = False,
        package: str | None = None,
        limit: int = 20,
    ) -> str:
        """Export import relationships aggregated by package, not by individual file."""
        packages = {
            path: self._package_name(path)
            for path in self._graph.nodes()
            if include_tests or not self._is_test_path(path)
        }
        relationships: dict[tuple[str, str], int] = {}
        for source, target in self._graph.edges():
            if source not in packages or target not in packages:
                continue
            pair = (packages[source], packages[target])
            if pair[0] == pair[1]:
                continue
            relationships[pair] = relationships.get(pair, 0) + 1
        if package:
            relationships = {
                pair: count
                for pair, count in relationships.items()
                if self._matches_scope(pair[0], package) or self._matches_scope(pair[1], package)
            }
        connected = {item for pair in relationships for item in pair}
        if not connected:
            scope = f" for {package}" if package else ""
            return f'flowchart LR\n    Empty["No package relationships detected{scope}"]\n'

        ordered = self._limit_packages(connected, relationships, limit)
        identifiers = {package: f"P{index}" for index, package in enumerate(ordered, 1)}
        lines = [
            "flowchart LR",
            "    %% Package A --> Package B means one or more imports from A to B.",
            "    classDef package fill:#F8FAFC,stroke:#7A8795,color:#1F2937;",
        ]
        if len(ordered) < len(connected):
            lines.append(
                f"    %% Reduced view: {len(ordered)} of {len(connected)} packages. "
                "Use --package to explore a specific area."
            )
        for package in ordered:
            lines.append(f'    {identifiers[package]}["{package}"]')
        for (source, target), count in sorted(relationships.items()):
            if source in identifiers and target in identifiers:
                lines.append(
                    f"    {identifiers[source]} -->|{count} imports| {identifiers[target]}"
                )
        lines.append(f"    class {','.join(identifiers.values())} package")
        return "\n".join(lines) + "\n"

    def file_mermaid(
        self,
        package: str | None = None,
        include_tests: bool = False,
        limit: int = 50,
    ) -> str:
        """Export a bounded file-level import map with a focused visual layout."""
        scoped = {
            path
            for path in self._graph.nodes()
            if (include_tests or not self._is_test_path(path))
            and (package is None or self._matches_scope(path, package))
        }
        candidates = set(scoped)
        if package:
            neighbors = {
                neighbor
                for node in scoped
                for neighbor in (*self._graph.predecessors(node), *self._graph.successors(node))
                if include_tests or not self._is_test_path(neighbor)
            }
            candidates.update(neighbors)
        if not candidates:
            scope = f" for {package}" if package else ""
            return f'graph TD\n    Empty["No Python files detected{scope}"]\n'
        selected = self._limit_files(candidates, scoped, limit)
        identifiers = {node: f"N{index}" for index, node in enumerate(sorted(selected), 1)}
        lines = [
            "flowchart LR",
            "    %% A --> B means file A imports file B.",
            (
                "    classDef selectedNode fill:#DCEEFF,stroke:#2E74B5,"
                "stroke-width:2px,color:#1F4D78;"
            ),
            "    classDef consumerNode fill:#F8FAFC,stroke:#7A8795,color:#1F2937;",
            "    classDef dependencyNode fill:#EEF7E9,stroke:#5A8F45,color:#1F3D2E;",
        ]
        if len(selected) < len(candidates):
            lines.append(
                f"    %% Reduced view: {len(selected)} of {len(candidates)} files. "
                "Use --package to narrow the scope."
            )
        if package:
            selected_inside = sorted(path for path in selected if path in scoped)
            selected_inside_set = set(selected_inside)
            consumers = {
                source
                for source, target in self._graph.edges()
                if target in selected_inside_set and source in selected
                and source not in selected_inside_set
            }
            dependencies = {
                target
                for source, target in self._graph.edges()
                if source in selected_inside_set and target in selected
                and target not in selected_inside_set
            }
            shared = consumers & dependencies
            consumers.difference_update(shared)
            dependencies.difference_update(shared)
            if selected_inside:
                lines.append('    subgraph Selected["Area seleccionada"]')
                lines.append("        direction TB")
                lines.extend(
                    f'        {identifiers[path]}["{self._file_label(path, package)}"]'
                    for path in selected_inside
                )
                lines.append("    end")
            if consumers:
                lines.append('    subgraph Consumers["Usan esta area"]')
                lines.append("        direction TB")
                lines.extend(
                    f'        {identifiers[path]}["{self._file_label(path, package)}"]'
                    for path in sorted(consumers)
                )
                lines.append("    end")
            if dependencies or shared:
                lines.append('    subgraph Dependencies["Dependencias directas"]')
                lines.append("        direction TB")
                lines.extend(
                    f'        {identifiers[path]}["{self._file_label(path, package)}"]'
                    for path in sorted(dependencies | shared)
                )
                lines.append("    end")
        else:
            lines.extend(f'    {identifier}["{path}"]' for path, identifier in identifiers.items())
        lines.extend(
            f"    {identifiers[source]} --> {identifiers[target]}"
            for source, target in sorted(self._graph.edges())
            if source in identifiers and target in identifiers
        )
        selected_nodes = ",".join(identifiers[path] for path in selected if path in scoped)
        if selected_nodes:
            lines.append(f"    class {selected_nodes} selectedNode")
        if package:
            consumer_nodes = ",".join(identifiers[path] for path in sorted(consumers))
            dependency_nodes = ",".join(
                identifiers[path] for path in sorted(dependencies | shared)
            )
            if consumer_nodes:
                lines.append(f"    class {consumer_nodes} consumerNode")
            if dependency_nodes:
                lines.append(f"    class {dependency_nodes} dependencyNode")
        return "\n".join(lines) + "\n"

    def class_mermaid(
        self,
        package: str | None = None,
        focus: str | None = None,
        limit: int = 25,
    ) -> str:
        """Export classes and inheritance only; runtime collaboration is intentionally excluded."""
        all_classes = [
            item
            for file in self._files
            if package is None or self._matches_scope(file.path, package)
            for item in file.classes
        ]
        if focus:
            focused = [item for item in all_classes if item.name == focus]
            if not focused:
                return f'classDiagram\n    Empty["Class {focus} was not found"]\n'
            all_classes = self._focus_classes(all_classes, focused)
        classes = sorted(
            all_classes,
            key=lambda item: (not item.bases, -len(item.methods), item.qualified_name),
        )[:limit]
        if not classes:
            return "classDiagram\n    class Empty[\"No Python classes detected\"]\n"
        identifiers = {
            item.qualified_name: self._class_identifier(item.qualified_name, index)
            for index, item in enumerate(classes, 1)
        }
        by_name = {item.name: item.qualified_name for item in classes}
        lines = ["classDiagram"]
        if len(classes) < len(all_classes):
            lines.append(
                f"    %% Reduced view: {len(classes)} of {len(all_classes)} classes. "
                "Use --package or --focus to narrow the scope."
            )
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

    def _package_name(self, path: str) -> str:
        parts = path.split("/")[:-1]
        if "src" in parts:
            parts = parts[parts.index("src") :]
        return "/".join(parts) if parts else "root"

    def _is_test_path(self, path: str) -> bool:
        parts = path.split("/")
        return "tests" in parts or parts[-1].startswith("test_")

    def _matches_scope(self, value: str, scope: str) -> bool:
        normalized_scope = scope.strip().replace("\\", "/").strip("/")
        normalized_value = value.replace("\\", "/").strip("/")
        return normalized_value == normalized_scope or f"/{normalized_scope}/" in (
            f"/{normalized_value}/"
        ) or normalized_value.startswith(f"{normalized_scope}/")

    def _limit_files(self, candidates: set[str], scoped: set[str], limit: int) -> set[str]:
        ranked_scope = sorted(scoped, key=lambda item: (-self._graph.degree(item), item))
        selected = ranked_scope[:limit]
        if len(selected) == limit:
            return set(selected)
        ranked_neighbors = sorted(
            candidates.difference(scoped), key=lambda item: (-self._graph.degree(item), item)
        )
        return set([*selected, *ranked_neighbors[: limit - len(selected)]])

    def _file_label(self, path: str, scope: str) -> str:
        normalized_scope = scope.strip().replace("\\", "/").strip("/")
        normalized_path = path.replace("\\", "/").strip("/")
        marker = f"/{normalized_scope}/"
        if marker in f"/{normalized_path}":
            return normalized_path.split(marker, maxsplit=1)[-1]
        parts = normalized_path.split("/")
        if "src" in parts:
            return "/".join(parts[parts.index("src") + 1 :])
        return normalized_path

    def _limit_packages(
        self,
        packages: set[str],
        relationships: dict[tuple[str, str], int],
        limit: int,
    ) -> list[str]:
        scores = {
            package: sum(
                count
                for (source, target), count in relationships.items()
                if package in {source, target}
            )
            for package in packages
        }
        return sorted(packages, key=lambda package: (-scores[package], package))[:limit]

    def _focus_classes(
        self, all_classes: list[ClassInfo], focused: list[ClassInfo]
    ) -> list[ClassInfo]:
        focused_names = {item.name for item in focused}
        parent_names = {
            base.split(".")[-1]
            for item in focused
            for base in item.bases
        }
        child_names = {
            item.name
            for item in all_classes
            if any(base.split(".")[-1] in focused_names for base in item.bases)
        }
        included = focused_names | parent_names | child_names
        return [item for item in all_classes if item.name in included]

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
                    f"    {identifiers[edge.source]} -->|{edge.imports_count} imports| "
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

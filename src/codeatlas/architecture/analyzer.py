"""Deterministic role and component inference for Python repositories."""

from collections import defaultdict
import re

from codeatlas.models import (
    ArchitectureAnalysis,
    ArchitectureComponent,
    ArchitectureDependency,
    ArchitectureRole,
    DependencyEdge,
    FileAnalysis,
)


class ArchitectureAnalyzer:
    """Infer broad architectural roles without executing or sending source code."""

    _ROLE_RULES: tuple[tuple[ArchitectureRole, tuple[str, ...]], ...] = (
        ("tests", ("test", "tests", "conftest")),
        (
            "configuration",
            ("config", "configuration", "setting", "settings", "environment", "env"),
        ),
        (
            "orchestration",
            ("agent", "agents", "orchestr", "workflow", "supervisor", "pipeline", "graph"),
        ),
        (
            "persistence",
            (
                "repository",
                "repositories",
                "database",
                "databases",
                "storage",
                "store",
                "dao",
                "persistence",
            ),
        ),
        ("service", ("service", "use_case", "usecase", "handler")),
        ("domain", ("model", "models", "entity", "schema", "domain", "dto")),
        ("infrastructure", ("client", "adapter", "integration", "infrastructure", "gateway")),
        (
            "entrypoint",
            ("cli", "main", "app", "api", "route", "routes", "view", "controller"),
        ),
    )

    _DISPLAY_NAMES: dict[ArchitectureRole, str] = {
        "entrypoint": "Entradas",
        "configuration": "Configuración",
        "orchestration": "Orquestación",
        "service": "Servicios",
        "domain": "Dominio y modelos",
        "persistence": "Persistencia",
        "infrastructure": "Infraestructura",
        "tests": "Pruebas",
        "unknown": "Sin clasificar",
    }

    def analyze(
        self, files: list[FileAnalysis], dependencies: list[DependencyEdge]
    ) -> ArchitectureAnalysis:
        assignments = {file.path: self._classify(file) for file in files}
        grouped: defaultdict[ArchitectureRole, list[tuple[FileAnalysis, list[str]]]] = (
            defaultdict(list)
        )
        for file in files:
            role, evidence = assignments[file.path]
            grouped[role].append((file, evidence))

        components = [
            ArchitectureComponent(
                name=self._DISPLAY_NAMES[role],
                role=role,
                files=sorted(file.path for file, _ in items),
                confidence=self._confidence(role, items),
                evidence=sorted({fact for _, facts in items for fact in facts})[:8],
            )
            for role, items in sorted(grouped.items(), key=lambda item: item[0])
        ]
        names = {role: self._DISPLAY_NAMES[role] for role in grouped}
        edges: defaultdict[tuple[str, str], list[str]] = defaultdict(list)
        for edge in dependencies:
            source_role = assignments.get(edge.source, ("unknown", []))[0]
            target_role = assignments.get(edge.target, ("unknown", []))[0]
            if source_role == target_role or "tests" in {source_role, target_role}:
                continue
            edges[(names[source_role], names[target_role])].append(edge.source)
        relationships = [
            ArchitectureDependency(
                source=source,
                target=target,
                imports_count=len(set(files)),
                evidence_files=sorted(set(files))[:5],
            )
            for (source, target), files in sorted(edges.items())
        ]
        return ArchitectureAnalysis(
            components=components,
            dependencies=relationships,
            entry_points=sorted(
                path for path, (role, _) in assignments.items() if role == "entrypoint"
            ),
        )

    def _classify(self, file: FileAnalysis) -> tuple[ArchitectureRole, list[str]]:
        path_tokens = self._path_tokens(file.path)
        for role, terms in self._ROLE_RULES:
            matched = [term for term in terms if term in path_tokens]
            if matched:
                return (
                    role,
                    [f"{file.path}: término de ruta {term!r}" for term in matched[:2]],
                )
        return "unknown", [f"{file.path}: sin término de ruta reconocido"]

    def _path_tokens(self, path: str) -> set[str]:
        """Return stable role hints from the file location, not its implementation details."""
        parts = path.lower().replace("\\", "/").split("/")
        if "src" in parts:
            parts = parts[parts.index("src") + 1 :]
        elif len(parts) > 1:
            parts = parts[1:]
        filtered_parts = [
            part for part in parts if part not in {"__init__.py", "__init__"}
        ]
        return {
            token
            for part in filtered_parts
            for token in re.findall(r"[a-z0-9]+", part)
        }

    def _confidence(
        self, role: ArchitectureRole, items: list[tuple[FileAnalysis, list[str]]]
    ) -> float:
        if role == "unknown":
            return 0.4
        return min(0.95, 0.65 + min(len(items), 3) * 0.1)

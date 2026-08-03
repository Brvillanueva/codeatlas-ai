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
        ("configuration", ("config", "setting", "environment", "env")),
        (
            "orchestration",
            ("agent", "orchestr", "workflow", "supervisor", "pipeline"),
        ),
        (
            "persistence",
            ("repository", "database", "storage", "store", "dao", "persistence"),
        ),
        ("service", ("service", "use_case", "usecase", "handler")),
        ("domain", ("model", "entity", "schema", "domain", "dto")),
        ("infrastructure", ("client", "adapter", "integration", "infrastructure", "gateway")),
        ("entrypoint", ("cli", "main", "app", "api", "route", "view", "controller")),
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
        searchable = " ".join(
            [
                file.path.lower(),
                file.module_name.lower(),
                (file.docstring or "").lower(),
                *(item.module.lower() for item in file.imports),
                *(item.name.lower() for item in file.classes),
                *(item.name.lower() for item in file.functions),
                *(decorator.lower() for item in file.classes for decorator in item.decorators),
                *(decorator.lower() for item in file.functions for decorator in item.decorators),
            ]
        )
        for role, terms in self._ROLE_RULES:
            matched = [
                term
                for term in terms
                if re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", searchable)
            ]
            if matched:
                return role, [f"{file.path}: coincidencia {term!r}" for term in matched[:2]]
        return "unknown", [f"{file.path}: sin patrón de rol reconocido"]

    def _confidence(
        self, role: ArchitectureRole, items: list[tuple[FileAnalysis, list[str]]]
    ) -> float:
        if role == "unknown":
            return 0.4
        return min(0.95, 0.65 + min(len(items), 3) * 0.1)

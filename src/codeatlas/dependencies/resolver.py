"""Resolve Python imports into internal and external dependencies."""

import sys
from collections import defaultdict
from collections.abc import Iterable

from codeatlas.models import DependencyEdge, FileAnalysis


class DependencyResolver:
    """Resolve imports using the modules found in the selected repository."""

    def resolve(self, files: list[FileAnalysis]) -> tuple[list[DependencyEdge], list[str]]:
        index = self._build_index(files)
        internal_roots = {module.split(".", maxsplit=1)[0] for module in index}
        edges: list[DependencyEdge] = []
        external: set[str] = set()
        for file in files:
            for import_info in file.imports:
                candidates = self._candidates(
                    file, import_info.module, import_info.imported_names, import_info.level
                )
                paths = self._resolve(candidates, index)
                if paths:
                    import_info.is_internal = True
                    import_info.classification = "internal"
                    import_info.resolved_paths = sorted(paths)
                    edges.extend(
                        DependencyEdge(
                            source=file.path, target=path, imported_module=import_info.module
                        )
                        for path in sorted(paths)
                        if path != file.path
                    )
                else:
                    root = self._external_root(import_info.module, import_info.imported_names)
                    if root in sys.stdlib_module_names or root == "__future__":
                        import_info.is_internal = False
                        import_info.classification = "standard_library"
                    elif root in internal_roots:
                        import_info.is_internal = None
                        import_info.classification = "unresolved_internal"
                    else:
                        import_info.is_internal = False
                        import_info.classification = "third_party"
                    if import_info.classification == "third_party" and root:
                        external.add(root)
        unique = {(edge.source, edge.target, edge.imported_module): edge for edge in edges}
        return list(unique.values()), sorted(external)

    def _candidates(
        self, file: FileAnalysis, module: str, names: list[str], level: int
    ) -> list[str]:
        if level == 0:
            candidates = [module] if module else []
        else:
            parts = file.module_name.split(".") if file.module_name else []
            package = (
                parts
                if file.path.endswith("/__init__.py") or file.path == "__init__.py"
                else parts[:-1]
            )
            base = ".".join(package[: len(package) - max(level - 1, 0)])
            candidates = [".".join(part for part in (base, module) if part)]
        base = candidates[0] if candidates else ""
        for name in names:
            clean_name = name.split(" as ", maxsplit=1)[0]
            if base and clean_name != "*":
                candidates.append(f"{base}.{clean_name}")
        return [candidate for candidate in candidates if candidate]

    def _build_index(self, files: list[FileAnalysis]) -> dict[str, set[str]]:
        """Index canonical modules and useful aliases for nested ``src`` layouts."""
        index: defaultdict[str, set[str]] = defaultdict(set)
        for file in files:
            if file.syntax_error:
                continue
            for module_name in self._module_aliases(file):
                index[module_name].add(file.path)
        return dict(index)

    def _module_aliases(self, file: FileAnalysis) -> set[str]:
        aliases = {file.module_name}
        parts = file.module_name.split(".")
        if "src" in parts:
            aliases.add(".".join(parts[parts.index("src") :]))
        return {alias for alias in aliases if alias}

    def _resolve(self, candidates: Iterable[str], index: dict[str, set[str]]) -> set[str]:
        return {path for candidate in candidates for path in index.get(candidate, set())}

    def _external_root(self, module: str, names: list[str]) -> str | None:
        if module:
            return module.split(".", maxsplit=1)[0]
        for name in names:
            root = name.split(" as ", maxsplit=1)[0].split(".", maxsplit=1)[0]
            if root and root != "*":
                return root
        return None

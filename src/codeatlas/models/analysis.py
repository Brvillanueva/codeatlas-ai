"""Validated, serializable models for static repository analysis."""

from typing import Literal

from pydantic import BaseModel, Field

ParameterKind = Literal[
    "positional_only",
    "positional_or_keyword",
    "var_positional",
    "keyword_only",
    "var_keyword",
]
ArchitectureRole = Literal[
    "entrypoint",
    "configuration",
    "orchestration",
    "service",
    "domain",
    "persistence",
    "infrastructure",
    "tests",
    "unknown",
]


class ParameterInfo(BaseModel):
    name: str
    annotation: str | None = None
    default: str | None = None
    kind: ParameterKind


class FunctionInfo(BaseModel):
    name: str
    qualified_name: str
    parameters: list[ParameterInfo] = Field(default_factory=list)
    return_type: str | None = None
    docstring: str | None = None
    decorators: list[str] = Field(default_factory=list)
    is_async: bool = False
    line_start: int
    line_end: int | None = None


class ClassInfo(BaseModel):
    name: str
    qualified_name: str
    bases: list[str] = Field(default_factory=list)
    methods: list[FunctionInfo] = Field(default_factory=list)
    docstring: str | None = None
    decorators: list[str] = Field(default_factory=list)
    line_start: int
    line_end: int | None = None


class ImportInfo(BaseModel):
    module: str
    imported_names: list[str] = Field(default_factory=list)
    alias: str | None = None
    level: int = 0
    is_internal: bool | None = None
    resolved_paths: list[str] = Field(default_factory=list)


class FileAnalysis(BaseModel):
    path: str
    module_name: str
    docstring: str | None = None
    imports: list[ImportInfo] = Field(default_factory=list)
    classes: list[ClassInfo] = Field(default_factory=list)
    functions: list[FunctionInfo] = Field(default_factory=list)
    line_count: int = 0
    syntax_error: str | None = None


class DependencyEdge(BaseModel):
    source: str
    target: str
    imported_module: str


class AnalysisError(BaseModel):
    path: str
    message: str
    kind: Literal["read_error", "syntax_error", "scanner_error"]


class RepositoryStats(BaseModel):
    files_discovered: int = 0
    python_files: int = 0
    classes: int = 0
    functions: int = 0
    methods: int = 0
    imports: int = 0
    internal_imports: int = 0
    external_dependencies: int = 0
    files_with_errors: int = 0


class ArchitectureComponent(BaseModel):
    """A role-based component inferred from static repository evidence."""

    name: str
    role: ArchitectureRole
    files: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    evidence: list[str] = Field(default_factory=list)


class ArchitectureDependency(BaseModel):
    """An aggregated dependency between inferred components."""

    source: str
    target: str
    imports_count: int = 0
    evidence_files: list[str] = Field(default_factory=list)


class ArchitectureAnalysis(BaseModel):
    """Deterministic, role-oriented view of a repository architecture."""

    components: list[ArchitectureComponent] = Field(default_factory=list)
    dependencies: list[ArchitectureDependency] = Field(default_factory=list)
    entry_points: list[str] = Field(default_factory=list)


class NarrativeEvidence(BaseModel):
    claim: str
    files: list[str] = Field(default_factory=list)


class ArchitectureNarrative(BaseModel):
    """Optional interpretation generated from selected repository evidence."""

    purpose: str
    component_responsibilities: dict[str, str] = Field(default_factory=dict)
    main_flow: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    evidence: list[NarrativeEvidence] = Field(default_factory=list)


class RepositoryAnalysis(BaseModel):
    repository_name: str
    repository_path: str
    files: list[FileAnalysis] = Field(default_factory=list)
    internal_dependencies: list[DependencyEdge] = Field(default_factory=list)
    external_dependencies: list[str] = Field(default_factory=list)
    central_modules: list[str] = Field(default_factory=list)
    architecture: ArchitectureAnalysis = Field(default_factory=ArchitectureAnalysis)
    errors: list[AnalysisError] = Field(default_factory=list)
    stats: RepositoryStats = Field(default_factory=RepositoryStats)

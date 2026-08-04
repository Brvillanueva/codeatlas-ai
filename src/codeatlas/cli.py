"""Console interface for CodeAtlas AI."""

from pathlib import Path
from typing import Annotated, Literal

import typer
from rich.console import Console
from rich.table import Table

from codeatlas import __version__
from codeatlas.ai import OpenAiArchitectureAnalyst
from codeatlas.application import RepositoryAnalyzer
from codeatlas.exceptions import CodeAtlasError, OutputAlreadyExistsError
from codeatlas.generators import JsonGenerator, WordReportGenerator
from codeatlas.models import RepositoryAnalysis

app = typer.Typer(
    name="codeatlas",
    help="Analyze Python repositories and map their architecture.",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()


def analysis_or_exit(repository: Path) -> RepositoryAnalysis:
    try:
        return RepositoryAnalyzer().analyze(repository)
    except CodeAtlasError as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1) from error


def print_summary(analysis: RepositoryAnalysis) -> None:
    stats = analysis.stats
    table = Table(title="CodeAtlas AI - Repository analysis completed")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")
    for label, value in (
        ("Repository", analysis.repository_name),
        ("Files discovered", stats.files_discovered),
        ("Python files", stats.python_files),
        ("Classes detected", stats.classes),
        ("Functions detected", stats.functions),
        ("Methods detected", stats.methods),
        ("Internal imports", stats.internal_imports),
        ("External dependencies", stats.external_dependencies),
        ("Files with errors", stats.files_with_errors),
    ):
        table.add_row(label, str(value))
    console.print(table)
    if analysis.central_modules:
        console.print("[bold]Central modules:[/bold] " + ", ".join(analysis.central_modules))
    if analysis.errors:
        console.print("[yellow]Analysis completed with non-fatal errors.[/yellow]")


@app.callback()
def main(
    version: Annotated[
        bool, typer.Option("--version", help="Show the installed CodeAtlas version.")
    ] = False,
) -> None:
    if version:
        console.print(f"CodeAtlas AI {__version__}")
        raise typer.Exit()


@app.command()
def inspect(
    repository: Annotated[Path, typer.Argument(help="Local repository to analyze.")],
) -> None:
    """Print a deterministic summary for a local Python repository."""
    print_summary(analysis_or_exit(repository))


@app.command()
def analyze(
    repository: Annotated[Path, typer.Argument(help="Local repository to analyze.")],
    output: Annotated[Path, typer.Option("--output", "-o", help="JSON file to create.")] = Path(
        "analysis.json"
    ),
    force: Annotated[
        bool, typer.Option("--force", help="Overwrite an existing output file.")
    ] = False,
) -> None:
    """Analyze a repository and export the complete result as JSON."""
    result = analysis_or_exit(repository)
    try:
        written = JsonGenerator().write(result, output, force=force)
    except CodeAtlasError as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1) from error
    print_summary(result)
    console.print(f"[green]JSON export:[/green] {written}")


@app.command()
def graph(
    repository: Annotated[Path, typer.Argument(help="Local repository to analyze.")],
    output: Annotated[Path, typer.Option("--output", "-o", help="Mermaid file to create.")] = Path(
        "dependencies.mmd"
    ),
    force: Annotated[
        bool, typer.Option("--force", help="Overwrite an existing output file.")
    ] = False,
    view: Annotated[
        Literal["executive", "technical"],
        typer.Option(
            "--view", help="Architecture view: executive (clean) or technical (complete)."
        ),
    ] = "technical",
) -> None:
    """Legacy graph command. Prefer dependencies or classes for explicit diagram types."""
    result = analysis_or_exit(repository)
    destination = output.expanduser().resolve()
    try:
        if destination.exists() and not force:
            raise OutputAlreadyExistsError(
                f"Output already exists: {destination}. Use --force to overwrite it."
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            RepositoryAnalyzer().dependency_graph(result).to_mermaid(
                view=view, architecture=result.architecture
            ),
            encoding="utf-8",
        )
    except CodeAtlasError as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1) from error
    console.print(f"[green]Mermaid graph ({view}):[/green] {destination}")
    if view == "executive":
        console.print(
            "[yellow]Experimental component hypothesis. "
            "It is not a validated architecture diagram.[/yellow]"
        )


@app.command()
def dependencies(
    repository: Annotated[Path, typer.Argument(help="Local repository to analyze.")],
    output: Annotated[Path, typer.Option("--output", "-o", help="Mermaid file to create.")] = Path(
        "dependencies.mmd"
    ),
    force: Annotated[
        bool, typer.Option("--force", help="Overwrite an existing output file.")
    ] = False,
    level: Annotated[
        Literal["package", "file"],
        typer.Option("--level", help="Package summary (default) or complete file-level imports."),
    ] = "package",
    include_tests: Annotated[
        bool, typer.Option("--include-tests", help="Include test packages in the package summary."),
    ] = False,
    package: Annotated[
        str | None,
        typer.Option("--package", help="Limit the diagram to a package, e.g. src/graph."),
    ] = None,
    limit: Annotated[
        int, typer.Option("--limit", min=1, help="Maximum nodes in the diagram (default: 20).")
    ] = 20,
) -> None:
    """Export detected imports by package or individual Python file."""
    result = analysis_or_exit(repository)
    destination = output.expanduser().resolve()
    try:
        if destination.exists() and not force:
            raise OutputAlreadyExistsError(
                f"Output already exists: {destination}. Use --force to overwrite it."
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        graph_model = RepositoryAnalyzer().dependency_graph(result)
        destination.write_text(
            graph_model.package_mermaid(
                include_tests=include_tests, package=package, limit=limit
            )
            if level == "package"
            else graph_model.file_mermaid(
                package=package, include_tests=include_tests, limit=limit
            ),
            encoding="utf-8",
        )
    except CodeAtlasError as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1) from error
    console.print(f"[green]Dependency diagram ({level}):[/green] {destination}")


@app.command()
def classes(
    repository: Annotated[Path, typer.Argument(help="Local repository to analyze.")],
    output: Annotated[Path, typer.Option("--output", "-o", help="Mermaid file to create.")] = Path(
        "classes.mmd"
    ),
    force: Annotated[
        bool, typer.Option("--force", help="Overwrite an existing output file.")
    ] = False,
    limit: Annotated[
        int, typer.Option("--limit", min=1, help="Maximum classes to include (default: 25).")
    ] = 25,
    package: Annotated[
        str | None,
        typer.Option("--package", help="Limit the diagram to a package, e.g. src/graph."),
    ] = None,
    focus: Annotated[
        str | None,
        typer.Option("--focus", help="Show one class plus direct inheritance relations."),
    ] = None,
) -> None:
    """Export a bounded class diagram with methods and detected inheritance."""
    result = analysis_or_exit(repository)
    destination = output.expanduser().resolve()
    try:
        if destination.exists() and not force:
            raise OutputAlreadyExistsError(
                f"Output already exists: {destination}. Use --force to overwrite it."
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            RepositoryAnalyzer().dependency_graph(result).class_mermaid(
                package=package, focus=focus, limit=limit
            ),
            encoding="utf-8",
        )
    except CodeAtlasError as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1) from error
    console.print(f"[green]Class diagram:[/green] {destination}")


@app.command(name="report")
def report(
    repository: Annotated[Path, typer.Argument(help="Local repository to analyze.")],
    output: Annotated[Path, typer.Option("--output", "-o", help="Word report to create.")] = Path(
        "codeatlas-report.docx"
    ),
    force: Annotated[
        bool, typer.Option("--force", help="Overwrite an existing output file.")
    ] = False,
    ai: Annotated[
        bool,
        typer.Option("--ai", help="Add an optional OpenAI interpretation using OPENAI_API_KEY."),
    ] = False,
) -> None:
    """Analyze a repository and export an editable Word architecture report."""
    result = analysis_or_exit(repository)
    try:
        narrative = OpenAiArchitectureAnalyst().analyze(result) if ai else None
        written = WordReportGenerator().write(result, output, force=force, narrative=narrative)
    except CodeAtlasError as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1) from error
    print_summary(result)
    console.print(f"[green]Word report:[/green] {written}")

"""JSON export for reproducible static-analysis results."""

from pathlib import Path

from codeatlas.exceptions import OutputAlreadyExistsError
from codeatlas.models import RepositoryAnalysis


class JsonGenerator:
    def write(self, analysis: RepositoryAnalysis, output_path: Path, force: bool = False) -> Path:
        output = output_path.expanduser().resolve()
        if output.exists() and not force:
            raise OutputAlreadyExistsError(
                f"Output already exists: {output}. Use --force to overwrite it."
            )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(analysis.model_dump_json(indent=2), encoding="utf-8")
        return output

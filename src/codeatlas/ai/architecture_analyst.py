"""Optional, evidence-bounded OpenAI architecture interpretation."""

import json
import os
from pathlib import Path
from typing import Any

from codeatlas.exceptions import AiAnalysisError, MissingApiKeyError
from codeatlas.models import ArchitectureNarrative, RepositoryAnalysis

_DEFAULT_MODEL = "gpt-5.6-terra"
_MAX_FILES = 8
_MAX_CHARS_PER_FILE = 1_800

_INSTRUCTIONS = """You are CodeAtlas AI, an architecture analyst for a Python repository.
Use only the supplied evidence. Do not claim that code executes, that an external system exists,
or that a business rule is true unless the evidence explicitly supports it. Every factual claim
must name one or more relative file paths. When evidence is insufficient, say so in
open_questions. Return JSON only, with this exact shape:
{
  "purpose": "string",
  "component_responsibilities": {"component name": "responsibility with evidence"},
  "main_flow": ["string"],
  "risks": ["string"],
  "open_questions": ["string"],
  "evidence": [{"claim": "string", "files": ["relative/path.py"]}]
}
Write in Spanish for a mixed technical and non-technical audience. Keep the result concise.
"""


class OpenAiArchitectureAnalyst:
    """Call one OpenAI analyst with a compact, selected repository evidence package."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._model = model or os.getenv("CODEATLAS_OPENAI_MODEL", _DEFAULT_MODEL)

    def analyze(self, analysis: RepositoryAnalysis) -> ArchitectureNarrative:
        if not self._api_key:
            raise MissingApiKeyError(
                "AI analysis requires OPENAI_API_KEY. It is only read from the environment."
            )
        try:
            from openai import OpenAI
        except ImportError as error:
            raise AiAnalysisError(
                "The optional AI dependency is missing. Run: python -m pip install -e \".[dev]\""
            ) from error

        prompt = self._prompt(analysis)
        try:
            response = OpenAI(api_key=self._api_key).responses.create(
                model=self._model,
                input=prompt,
                reasoning={"effort": "medium"},
                text={"verbosity": "high"},
                store=False,
            )
        except Exception as error:
            raise AiAnalysisError(f"OpenAI architecture analysis failed: {error}") from error
        return self._parse_response(response.output_text)

    def _prompt(self, analysis: RepositoryAnalysis) -> str:
        evidence = {
            "repository_name": analysis.repository_name,
            "stats": analysis.stats.model_dump(),
            "components": [item.model_dump() for item in analysis.architecture.components],
            "component_dependencies": [
                item.model_dump() for item in analysis.architecture.dependencies
            ],
            "entry_points": analysis.architecture.entry_points,
            "external_dependencies": analysis.external_dependencies,
            "selected_source_extracts": self._source_extracts(analysis),
        }
        serialized_evidence = json.dumps(evidence, ensure_ascii=False)
        return f"{_INSTRUCTIONS}\n\nRepository evidence:\n{serialized_evidence}"

    def _source_extracts(self, analysis: RepositoryAnalysis) -> list[dict[str, str]]:
        root = Path(analysis.repository_path)
        role_by_path = {
            path: component.role
            for component in analysis.architecture.components
            if component.role != "tests"
            for path in component.files
        }
        priority = {
            "entrypoint": 0,
            "orchestration": 1,
            "service": 2,
            "domain": 3,
            "persistence": 4,
            "infrastructure": 5,
            "configuration": 6,
            "unknown": 7,
        }
        candidates = sorted(
            (
                file
                for file in analysis.files
                if file.path in role_by_path and not file.syntax_error
            ),
            key=lambda item: (priority.get(role_by_path[item.path], 8), item.path),
        )[:_MAX_FILES]
        extracts: list[dict[str, str]] = []
        for file in candidates:
            try:
                source = (root / file.path).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            extracts.append({"path": file.path, "source": source[:_MAX_CHARS_PER_FILE]})
        return extracts

    def _parse_response(self, text: str) -> ArchitectureNarrative:
        raw = text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", maxsplit=1)[1].rsplit("```", maxsplit=1)[0].strip()
        try:
            payload: dict[str, Any] = json.loads(raw)
            return ArchitectureNarrative.model_validate(payload)
        except (json.JSONDecodeError, ValueError) as error:
            raise AiAnalysisError("OpenAI returned an invalid architecture narrative.") from error

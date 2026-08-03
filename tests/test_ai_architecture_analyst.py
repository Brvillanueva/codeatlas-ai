import pytest

from codeatlas.ai.architecture_analyst import OpenAiArchitectureAnalyst
from codeatlas.exceptions import MissingApiKeyError


def test_ai_analysis_requires_environment_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    analyst = OpenAiArchitectureAnalyst()

    with pytest.raises(MissingApiKeyError):
        analyst.analyze(None)  # type: ignore[arg-type]


def test_ai_response_requires_the_narrative_contract() -> None:
    analyst = OpenAiArchitectureAnalyst(api_key="test-key")
    narrative = analyst._parse_response(
        '{"purpose":"Gestiona tareas","component_responsibilities":{"Servicios":"Coordina"},'
        '"main_flow":["Entrada -> Servicios"],"risks":[],"open_questions":[],"
        '"evidence":[{"claim":"Hay un servicio","files":["service.py"]}]}'
    )

    assert narrative.purpose == "Gestiona tareas"
    assert narrative.evidence[0].files == ["service.py"]

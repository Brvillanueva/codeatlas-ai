from pathlib import Path

from codeatlas.parsers import PythonAstParser

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "simple_project"


def test_parser_extracts_symbols_and_parameters() -> None:
    result = PythonAstParser().parse(FIXTURE_ROOT / "package" / "service.py", FIXTURE_ROOT)

    assert result.module_name == "package.service"
    assert result.classes[0].name == "UserService"
    assert result.classes[0].methods[0].name == "greet"
    assert result.classes[0].methods[0].parameters[2].default == "'Hello'"
    assert result.functions[0].name == "fetch_user"
    assert result.functions[0].is_async is True
    assert result.imports[0].module == "models"
    assert result.imports[0].level == 1


def test_parser_keeps_syntax_errors_inside_result() -> None:
    root = Path(__file__).parent / "fixtures" / "project_with_syntax_error"

    result = PythonAstParser().parse(root / "broken.py", root)

    assert result.syntax_error is not None
    assert result.classes == []

"""Python static analysis using the standard-library AST."""

import ast
import tokenize
from pathlib import Path

from codeatlas.models import (
    ClassInfo,
    FileAnalysis,
    FunctionInfo,
    ImportInfo,
    ParameterInfo,
    ParameterKind,
)


class PythonAstParser:
    """Extract deterministic metadata from Python source files."""

    def parse(self, file_path: Path, repository_root: Path) -> FileAnalysis:
        relative = file_path.relative_to(repository_root)
        module = self._module_name(relative)
        try:
            with tokenize.open(file_path) as source_file:
                source = source_file.read()
        except (OSError, SyntaxError, UnicodeDecodeError) as error:
            return FileAnalysis(
                path=relative.as_posix(), module_name=module, syntax_error=str(error)
            )
        lines = source.count("\n") + (1 if source else 0)
        try:
            tree = ast.parse(source, filename=str(file_path), type_comments=True)
        except SyntaxError as error:
            return FileAnalysis(
                path=relative.as_posix(),
                module_name=module,
                line_count=lines,
                syntax_error=self._syntax_error(error),
            )
        classes: list[ClassInfo] = []
        functions: list[FunctionInfo] = []
        imports: list[ImportInfo] = []
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(self._function(node, module))
            elif isinstance(node, ast.ClassDef):
                classes.append(self._class(node, module))
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.extend(self._imports(node))
        return FileAnalysis(
            path=relative.as_posix(),
            module_name=module,
            docstring=ast.get_docstring(tree),
            imports=imports,
            classes=classes,
            functions=functions,
            line_count=lines,
        )

    def _module_name(self, path: Path) -> str:
        parts = list(path.with_suffix("").parts)
        if parts[-1] == "__init__":
            parts.pop()
        return ".".join(parts) if parts else path.parent.name

    def _class(self, node: ast.ClassDef, module: str) -> ClassInfo:
        qualified = f"{module}.{node.name}"
        methods = [
            self._function(child, qualified)
            for child in node.body
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        return ClassInfo(
            name=node.name,
            qualified_name=qualified,
            bases=[self._text(base) for base in node.bases],
            methods=methods,
            docstring=ast.get_docstring(node),
            decorators=[self._text(item) for item in node.decorator_list],
            line_start=node.lineno,
            line_end=getattr(node, "end_lineno", None),
        )

    def _function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, parent: str) -> FunctionInfo:
        return FunctionInfo(
            name=node.name,
            qualified_name=f"{parent}.{node.name}",
            parameters=self._parameters(node.args),
            return_type=self._text(node.returns) if node.returns else None,
            docstring=ast.get_docstring(node),
            decorators=[self._text(item) for item in node.decorator_list],
            is_async=isinstance(node, ast.AsyncFunctionDef),
            line_start=node.lineno,
            line_end=getattr(node, "end_lineno", None),
        )

    def _parameters(self, arguments: ast.arguments) -> list[ParameterInfo]:
        result: list[ParameterInfo] = []
        positional = [*arguments.posonlyargs, *arguments.args]
        defaults = [None] * (len(positional) - len(arguments.defaults)) + list(arguments.defaults)
        for index, (argument, default) in enumerate(zip(positional, defaults, strict=True)):
            kind: ParameterKind = (
                "positional_only" if index < len(arguments.posonlyargs) else "positional_or_keyword"
            )
            result.append(self._parameter(argument, default, kind))
        if arguments.vararg:
            result.append(self._parameter(arguments.vararg, None, "var_positional"))
        for argument, default in zip(arguments.kwonlyargs, arguments.kw_defaults, strict=True):
            result.append(self._parameter(argument, default, "keyword_only"))
        if arguments.kwarg:
            result.append(self._parameter(arguments.kwarg, None, "var_keyword"))
        return result

    def _parameter(
        self,
        argument: ast.arg,
        default: ast.expr | None,
        kind: ParameterKind,
    ) -> ParameterInfo:
        return ParameterInfo(
            name=argument.arg,
            annotation=self._text(argument.annotation) if argument.annotation else None,
            default=self._text(default) if default else None,
            kind=kind,
        )

    def _imports(self, node: ast.Import | ast.ImportFrom) -> list[ImportInfo]:
        if isinstance(node, ast.Import):
            return [ImportInfo(module=item.name, alias=item.asname) for item in node.names]
        names = [
            item.name if item.asname is None else f"{item.name} as {item.asname}"
            for item in node.names
        ]
        return [ImportInfo(module=node.module or "", imported_names=names, level=node.level)]

    def _text(self, node: ast.AST | None) -> str:
        if node is None:
            return ""
        try:
            return ast.unparse(node)
        except ValueError:
            return type(node).__name__

    def _syntax_error(self, error: SyntaxError) -> str:
        return f"{error.msg} (line {error.lineno or 'unknown'})"

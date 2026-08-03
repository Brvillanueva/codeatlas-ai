# ADR 0001: Use Python AST for deterministic analysis

- Status: Accepted

## Decision

Use Python's standard `ast` module to extract modules, symbols, docstrings, decorators, annotations and imports.

## Consequences

The core works offline and remains reproducible. Syntax errors are captured per file without stopping repository analysis.

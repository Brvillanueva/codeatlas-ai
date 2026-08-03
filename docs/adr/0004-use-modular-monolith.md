# ADR 0004: Use a modular monolith for the MVP

- Status: Accepted

## Decision

Keep the backend as one Python package with bounded modules: scanner, parsers, dependencies, graph, generators and application services.

## Consequences

The project stays easy to run and test while preserving seams for a future FastAPI layer and independent frontend.

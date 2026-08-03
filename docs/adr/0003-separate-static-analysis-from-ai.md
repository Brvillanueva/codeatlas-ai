# ADR 0003: Separate static analysis from AI interpretation

- Status: Accepted

## Decision

Build scanner, parser, dependency resolution and graph generation independently from any AI provider. Future providers receive structured analysis rather than raw repositories by default.

## Consequences

The project works without network access and can support OpenAI, Claude, Gemini or local models later.

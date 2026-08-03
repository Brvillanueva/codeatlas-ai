"""Domain models."""


class User:
    """A user in the example project."""

    def __init__(self, name: str) -> None:
        self.name = name

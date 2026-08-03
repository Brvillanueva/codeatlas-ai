"""Example application entry point."""

from package.service import UserService


def main() -> str:
    """Run the example application."""
    return UserService().greet("Ada")

"""Service layer."""

from .models import User


class UserService:
    """Coordinates user-related behavior."""

    def greet(self, name: str, greeting: str = "Hello") -> str:
        """Return a greeting for one user."""
        user = User(name)
        return f"{greeting}, {user.name}!"


async def fetch_user(name: str) -> User:
    """Create a user asynchronously."""
    return User(name)

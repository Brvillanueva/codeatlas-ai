"""Domain exceptions exposed by CodeAtlas."""


class CodeAtlasError(Exception):
    """Base exception for expected CodeAtlas failures."""


class InvalidRepositoryError(CodeAtlasError):
    """Raised when the selected repository path is invalid."""


class OutputAlreadyExistsError(CodeAtlasError):
    """Raised when an export would overwrite an existing file."""


class MissingApiKeyError(CodeAtlasError):
    """Raised when an optional AI analysis is requested without an API key."""


class AiAnalysisError(CodeAtlasError):
    """Raised when an external AI response cannot be used safely."""

"""Custom exception classes for SentinelDoc backend."""
from typing import Optional, Any


class SentinelDocException(Exception):
    """Base exception for all SentinelDoc operational errors."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: Optional[Any] = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


class EmptyFileException(SentinelDocException):
    """Raised when an uploaded file is 0 bytes."""

    def __init__(self, message: str = "Uploaded file is empty (0 bytes)."):
        super().__init__(
            code="EMPTY_FILE",
            message=message,
            status_code=400,
        )


class UnsupportedFileTypeException(SentinelDocException):
    """Raised when an uploaded file extension/format is not supported."""

    def __init__(self, file_name: str, supported: str = "PDF, DOCX, CSV, XLSX, TXT"):
        super().__init__(
            code="UNSUPPORTED_FILE_TYPE",
            message=f"Unsupported file type for '{file_name}'. Supported formats: {supported}.",
            status_code=400,
        )


class MalformedFileException(SentinelDocException):
    """Raised when a file cannot be parsed or has invalid binary structures."""

    def __init__(self, message: str = "File is corrupt, damaged, or cannot be parsed."):
        super().__init__(
            code="MALFORMED_FILE",
            message=message,
            status_code=400,
        )


class InvalidParametersException(SentinelDocException):
    """Raised when parameters fail validation."""

    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            code="INVALID_PARAMETERS",
            message=message,
            status_code=422,
            details=details,
        )

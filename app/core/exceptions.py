"""Custom application exceptions for Geospatial File Measurement API."""

class GFMException(Exception):
    """Base exception for all application errors."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ResourceNotFoundError(GFMException):
    """Raised when a requested resource is not found."""
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class InvalidFileError(GFMException):
    """Raised when an uploaded file is invalid or unsupported."""
    def __init__(self, message: str = "Invalid file format or content"):
        super().__init__(message, status_code=400)


class CorruptedArchiveError(GFMException):
    """Raised when a zip archive is invalid or missing required shapefile components."""
    def __init__(self, message: str = "Corrupted or incomplete archive"):
        super().__init__(message, status_code=400)


class ParsingError(GFMException):
    """Raised when parsing geospatial features fails."""
    def __init__(self, message: str = "Failed to parse geospatial data"):
        super().__init__(message, status_code=422)


class CRSTransformationError(GFMException):
    """Raised when coordinate reference system transformation fails."""
    def __init__(self, message: str = "Failed to transform coordinate reference system"):
        super().__init__(message, status_code=422)

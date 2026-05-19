class DocumentDomainError(Exception):
    """Base exception for all document-related domain errors."""
    pass


class InvalidFileFormatError(DocumentDomainError):
    """Raised when the uploaded file is not a valid PDF."""
    pass


class FileSizeLimitExceededError(DocumentDomainError):
    """Raised when the uploaded file exceeds the maximum allowed size."""
    pass


class ExtractionFailedError(DocumentDomainError):
    """Raised when text or structural extraction from the document fails."""
    pass


class OCRFailureError(DocumentDomainError):
    """Raised when the OCR fallback process fails."""
    pass

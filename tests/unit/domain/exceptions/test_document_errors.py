from app.domain.exceptions.document_errors import (
    DocumentDomainError,
    ExtractionFailedError,
    FileSizeLimitExceededError,
    InvalidFileFormatError,
    OCRFailureError,
)


def test_document_exceptions_are_exceptions():
    assert issubclass(DocumentDomainError, Exception)
    assert issubclass(InvalidFileFormatError, DocumentDomainError)
    assert issubclass(FileSizeLimitExceededError, DocumentDomainError)
    assert issubclass(ExtractionFailedError, DocumentDomainError)
    assert issubclass(OCRFailureError, DocumentDomainError)

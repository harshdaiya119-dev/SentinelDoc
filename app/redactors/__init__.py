"""Multi-format redaction package."""
import os
from typing import List, Optional, Set
from app.models.schemas import Finding
from app.config import SUPPORTED_EXTENSIONS
from app.utils.exceptions import (
    EmptyFileException,
    UnsupportedFileTypeException,
    MalformedFileException,
)
from .base import BaseRedactor
from .pdf_redactor import PdfRedactor
from .docx_redactor import DocxRedactor
from .spreadsheet_redactor import SpreadsheetRedactor
from .txt_redactor import TxtRedactor

__all__ = [
    "BaseRedactor",
    "PdfRedactor",
    "DocxRedactor",
    "SpreadsheetRedactor",
    "TxtRedactor",
    "redact_document",
]


def redact_document(
    content: bytes,
    file_name: str,
    findings: List[Finding],
    target_finding_ids: Optional[Set[str]] = None,
) -> bytes:
    """Dispatch document redaction to format-specific redactor.

    Args:
        content: Raw document binary bytes.
        file_name: Uploaded file name.
        findings: All detected findings in the document.
        target_finding_ids: Optional set of finding IDs to selectively redact.
                            If None, all findings are redacted.

    Returns:
        Redacted document binary bytes.
    """
    if not content or len(content) == 0:
        raise EmptyFileException(f"Uploaded file '{file_name}' is empty (0 bytes).")

    _, ext = os.path.splitext(file_name.lower())
    if ext not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileTypeException(file_name)

    # Magic byte validation
    if ext == ".pdf":
        if b"%PDF-" not in content[:1024]:
            raise MalformedFileException(f"File '{file_name}' is corrupt or missing standard PDF header.")
    elif ext in (".docx", ".xlsx"):
        if not content.startswith(b"PK\x03\x04"):
            raise MalformedFileException(f"File '{file_name}' is corrupt or missing standard Office Open XML header.")

    try:
        if ext == ".pdf":
            return PdfRedactor().redact(content, file_name, findings, target_finding_ids)
        elif ext == ".docx":
            return DocxRedactor().redact(content, file_name, findings, target_finding_ids)
        elif ext in (".xlsx", ".csv"):
            return SpreadsheetRedactor().redact(content, file_name, findings, target_finding_ids)
        elif ext in (".txt", ".log"):
            return TxtRedactor().redact(content, file_name, findings, target_finding_ids)
        else:
            raise UnsupportedFileTypeException(file_name)
    except (EmptyFileException, UnsupportedFileTypeException, MalformedFileException):
        raise
    except Exception as e:
        raise MalformedFileException(f"Unable to redact '{file_name}': {str(e)}") from e

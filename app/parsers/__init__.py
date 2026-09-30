"""Document parsers package with unified scanning dispatcher."""
import os
from typing import List
from app.models.schemas import ScanResponse, Finding
from app.config import SUPPORTED_EXTENSIONS
from app.utils.exceptions import (
    EmptyFileException,
    UnsupportedFileTypeException,
    MalformedFileException,
)
from .pdf_parser import PdfParser
from .docx_parser import DocxParser
from .spreadsheet_parser import SpreadsheetParser
from .txt_parser import TxtParser

__all__ = [
    "PdfParser",
    "DocxParser",
    "SpreadsheetParser",
    "TxtParser",
    "scan_document",
]


def scan_document(content: bytes, file_name: str) -> ScanResponse:
    """Validate and dispatch document parsing, returning structured ScanResponse.

    Args:
        content: Raw document binary bytes.
        file_name: Name of the uploaded file.

    Returns:
        ScanResponse containing file metadata and list of Finding objects.

    Raises:
        EmptyFileException: If content is empty (0 bytes).
        UnsupportedFileTypeException: If file extension is unsupported.
        MalformedFileException: If file is corrupted or fails structural validation.
    """
    # 1. Check for empty file
    if not content or len(content) == 0:
        raise EmptyFileException(f"Uploaded file '{file_name}' is empty (0 bytes).")

    # 2. Extract and validate extension
    _, ext = os.path.splitext(file_name.lower())
    if ext not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileTypeException(file_name)

    file_type = ext.lstrip(".")

    # 3. Magic bytes / header integrity checks
    if ext == ".pdf":
        if b"%PDF-" not in content[:1024]:
            raise MalformedFileException(f"File '{file_name}' is corrupt or missing standard PDF header.")
    elif ext in (".docx", ".xlsx"):
        if not content.startswith(b"PK\x03\x04"):
            raise MalformedFileException(f"File '{file_name}' is corrupt or missing standard Office Open XML header.")

    # 4. Dispatch to appropriate parser
    try:
        findings: List[Finding]
        if ext == ".pdf":
            findings = PdfParser().parse_and_scan(content, file_name)
        elif ext == ".docx":
            findings = DocxParser().parse_and_scan(content, file_name)
        elif ext in (".xlsx", ".csv"):
            findings = SpreadsheetParser().parse_and_scan(content, file_name)
        elif ext in (".txt", ".log"):
            findings = TxtParser().parse_and_scan(content, file_name)
        else:
            raise UnsupportedFileTypeException(file_name)
    except (EmptyFileException, UnsupportedFileTypeException, MalformedFileException):
        raise
    except Exception as e:
        raise MalformedFileException(f"Unable to parse '{file_name}': {str(e)}") from e

    return ScanResponse(
        file_name=file_name,
        file_type=file_type,
        total_findings=len(findings),
        findings=findings,
    )

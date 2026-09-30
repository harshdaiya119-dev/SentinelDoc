"""Abstract base class for multi-format document redactors."""
from abc import ABC, abstractmethod
from typing import List, Optional, Set
from app.models.schemas import Finding


class BaseRedactor(ABC):
    """Abstract base redactor interface for all supported document formats."""

    @abstractmethod
    def redact(
        self,
        content: bytes,
        file_name: str,
        findings: List[Finding],
        target_finding_ids: Optional[Set[str]] = None,
    ) -> bytes:
        """Redact sensitive findings from the document and return modified binary bytes.

        Args:
            content: Raw original document binary bytes.
            file_name: Name of the uploaded file.
            findings: All detected findings in the document.
            target_finding_ids: Optional set of finding IDs to selectively redact.
                               If None, all findings in `findings` are redacted.

        Returns:
            Redacted binary file bytes.
        """
        pass

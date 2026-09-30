"""Document parser interfaces and data structures."""
from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel
from app.models.schemas import Location, BoundingBox


class ParsedSegment(BaseModel):
    """A segment of text extracted from a document with structural location metadata."""
    text: str
    location_template: Location
    page_number: Optional[int] = None

    def create_location(
        self,
        start_char: int,
        end_char: int,
        bbox: Optional[BoundingBox] = None,
    ) -> Location:
        """Create a full location object for a finding within this segment."""
        loc = self.location_template.model_copy()
        loc.start_char = start_char
        loc.end_char = end_char
        if bbox is not None:
            loc.bbox = bbox
        return loc


class BaseDocumentParser(ABC):
    """Abstract base class for format-specific document parsers."""

    @abstractmethod
    def parse_bytes(self, content: bytes, file_name: str) -> List[ParsedSegment]:
        """Extract text segments with spatial / structural locations from raw bytes.

        Args:
            content: Raw document binary bytes.
            file_name: Name of the file being parsed.

        Returns:
            List of ParsedSegment objects.
        """
        pass

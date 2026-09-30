"""Plain text parser with line number and character offset mapping."""
from typing import List
from app.models.schemas import Finding, Location
from app.core.presidio_engine import get_presidio_engine


class TxtParser:
    """Extracts text and line-level coordinates from plain text files."""

    def __init__(self):
        self.engine = get_presidio_engine()

    def parse_and_scan(self, content: bytes, file_name: str, start_id: int = 1) -> List[Finding]:
        """Scan TXT content and return findings mapped to line numbers and character offsets."""
        findings: List[Finding] = []
        curr_id = start_id

        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = content.decode("utf-8-sig")
            except UnicodeDecodeError:
                try:
                    text = content.decode("latin-1")
                except Exception as e:
                    raise ValueError(f"Failed to decode text file: {e}") from e

        lines = text.splitlines()
        for line_idx, line in enumerate(lines, start=1):
            if not line or not line.strip():
                continue

            detected_items = self.engine.analyze_text(line)
            for item in detected_items:
                location = Location(
                    line=line_idx,
                    start_char=item.start,
                    end_char=item.end,
                )
                findings.append(
                    Finding(
                        id=f"find_{curr_id}",
                        entity_type=item.entity_type,
                        matched_text=item.matched_text,
                        confidence=item.confidence,
                        reasoning=item.reasoning,
                        location=location,
                    )
                )
                curr_id += 1

        return findings

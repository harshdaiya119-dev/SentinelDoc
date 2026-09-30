"""PDF document parser using PyMuPDF (fitz) for text and bounding box coordinate extraction."""
from typing import List, Dict
import fitz
from app.models.schemas import Finding, Location, BoundingBox
from app.core.presidio_engine import get_presidio_engine


class PdfParser:
    """Extracts text and exact bounding box coordinates from PDF documents."""

    def __init__(self):
        self.engine = get_presidio_engine()

    def parse_and_scan(self, content: bytes, file_name: str, start_id: int = 1) -> List[Finding]:
        """Scan PDF content and return findings with exact page and bbox coordinates."""
        findings: List[Finding] = []
        curr_id = start_id

        try:
            doc = fitz.open(stream=content, filetype="pdf")
        except Exception as e:
            raise ValueError(f"Failed to open PDF file: {e}") from e

        try:
            for page_idx in range(len(doc)):
                page_num = page_idx + 1
                page = doc[page_idx]
                text = page.get_text()

                if not text or not text.strip():
                    continue

                detected_items = self.engine.analyze_text(text)
                # Track occurrences of matched texts on this page for multi-instance coordinate mapping
                occurrence_tracker: Dict[str, int] = {}

                for item in detected_items:
                    search_str = item.matched_text
                    occ = occurrence_tracker.get(search_str, 0)
                    occurrence_tracker[search_str] = occ + 1

                    # Search for word / phrase bounding box on the page
                    rects = page.search_for(search_str)
                    bbox: BoundingBox
                    if rects and occ < len(rects):
                        target_rect = rects[occ]
                        bbox = BoundingBox(
                            x0=round(float(target_rect.x0), 2),
                            top=round(float(target_rect.y0), 2),
                            x1=round(float(target_rect.x1), 2),
                            bottom=round(float(target_rect.y1), 2),
                        )
                    elif rects:
                        # Fallback to first occurrence rect
                        target_rect = rects[0]
                        bbox = BoundingBox(
                            x0=round(float(target_rect.x0), 2),
                            top=round(float(target_rect.y0), 2),
                            x1=round(float(target_rect.x1), 2),
                            bottom=round(float(target_rect.y1), 2),
                        )
                    else:
                        # Try searching without spaces / dashes if text was formatted differently
                        clean_str = "".join(c for c in search_str if c.isalnum())
                        fallback_rects = page.search_for(clean_str) if clean_str else []
                        if fallback_rects:
                            target_rect = fallback_rects[0]
                            bbox = BoundingBox(
                                x0=round(float(target_rect.x0), 2),
                                top=round(float(target_rect.y0), 2),
                                x1=round(float(target_rect.x1), 2),
                                bottom=round(float(target_rect.y1), 2),
                            )
                        else:
                            # Default fallback bounding box
                            bbox = BoundingBox(x0=0.0, top=0.0, x1=0.0, bottom=0.0)

                    location = Location(
                        page=page_num,
                        bbox=bbox,
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
        finally:
            doc.close()

        return findings

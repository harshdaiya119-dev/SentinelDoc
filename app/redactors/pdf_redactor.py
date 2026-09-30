"""PDF document redactor using PyMuPDF (fitz)."""
from typing import List, Optional, Set, Dict
import fitz
from app.models.schemas import Finding
from .base import BaseRedactor


class PdfRedactor(BaseRedactor):
    """Redacts PDF documents with exact bounding box solid black overlays."""

    def redact(
        self,
        content: bytes,
        file_name: str,
        findings: List[Finding],
        target_finding_ids: Optional[Set[str]] = None,
    ) -> bytes:
        """Apply exact bounding box solid black overlays to PDF document."""
        if target_finding_ids is not None:
            to_redact = [f for f in findings if f.id in target_finding_ids]
        else:
            to_redact = list(findings)

        try:
            doc = fitz.open(stream=content, filetype="pdf")
        except Exception as e:
            raise ValueError(f"Failed to open PDF document for redaction: {e}") from e

        try:
            # Group findings by 1-indexed page
            findings_by_page: Dict[int, List[Finding]] = {}
            for f in to_redact:
                page_num = f.location.page if (f.location and f.location.page) else 1
                findings_by_page.setdefault(page_num, []).append(f)

            for page_idx in range(len(doc)):
                page_num = page_idx + 1
                page_findings = findings_by_page.get(page_num, [])
                if not page_findings:
                    continue

                page = doc[page_idx]

                for f in page_findings:
                    annot_added = False

                    # 1. Use finding's bbox if valid
                    if f.location and f.location.bbox:
                        b = f.location.bbox
                        if b.x1 > b.x0 and b.bottom > b.top:
                            rect = fitz.Rect(b.x0, b.top, b.x1, b.bottom)
                            page.add_redact_annot(rect, fill=(0, 0, 0))
                            annot_added = True

                    # 2. Also search for matched_text on this page to handle multi-line wraps
                    if f.matched_text and f.matched_text.strip():
                        rects = page.search_for(f.matched_text)
                        if rects:
                            if f.location and f.location.bbox and annot_added:
                                b_rect = fitz.Rect(
                                    f.location.bbox.x0,
                                    f.location.bbox.top,
                                    f.location.bbox.x1,
                                    f.location.bbox.bottom,
                                )
                                for r in rects:
                                    if b_rect.intersects(r):
                                        page.add_redact_annot(r, fill=(0, 0, 0))
                            else:
                                for r in rects:
                                    page.add_redact_annot(r, fill=(0, 0, 0))
                                annot_added = True

                    # 3. Fallback for formatted alphanumeric strings
                    if not annot_added and f.matched_text:
                        clean_str = "".join(c for c in f.matched_text if c.isalnum())
                        if clean_str:
                            clean_rects = page.search_for(clean_str)
                            for r in clean_rects:
                                page.add_redact_annot(r, fill=(0, 0, 0))

                # Apply redactions to permanently remove underlying text and render solid black overlays
                page.apply_redactions()

            output_bytes = doc.tobytes(deflate=True)
            return output_bytes
        finally:
            doc.close()

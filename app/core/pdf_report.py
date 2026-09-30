"""Enterprise compliance audit PDF report generation engine for SentinelDoc.

Constructs multi-page, executive-ready PDF audit reports using ReportLab Platypus,
complete with two-pass dynamic NumberedCanvas pagination, corporate cybersecurity
styling, executive risk metric badges, entity breakdown tables, and privacy-preserving
masked finding logs.
"""
import io
import re
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Union

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable,
)
from reportlab.pdfgen import canvas

from app.models.schemas import Finding, ScanResponse
from app.core.risk import (
    calculate_risk_profile,
    normalize_entity_type,
    get_entity_severity,
)


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas recording page states to compute dynamic 'Page X of Y'."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, num_pages: int):
        """Draw running header and running footer with compliance disclaimer."""
        self.saveState()
        page_w, page_h = self._pagesize

        # Running header on subsequent pages
        if self._pageNumber > 1:
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(colors.HexColor("#0F172A"))
            self.drawString(36, page_h - 26, "SENTINELDOC COMPLIANCE AUDIT REPORT")

            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#64748B"))
            self.drawRightString(page_w - 36, page_h - 26, "RESTRICTED — INTERNAL COMPLIANCE USE")

            self.setStrokeColor(colors.HexColor("#E2E8F0"))
            self.setLineWidth(0.5)
            self.line(36, page_h - 30, page_w - 36, page_h - 30)

        # Running footer on all pages
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(36, 36, page_w - 36, 36)

        self.setFont("Helvetica", 7.5)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawString(
            36,
            24,
            "CONFIDENTIAL & PROPRIETARY — SentinelDoc Compliance Audit | Safe-Harbor Masked Data",
        )

        page_str = f"Page {self._pageNumber} of {num_pages}"
        self.drawRightString(page_w - 36, 24, page_str)

        self.restoreState()


def mask_pii(text: str, entity_type: str) -> str:
    """Mask sensitive PII string for privacy-preserving audit logs.

    Examples:
        - AADHAAR: XXXX-XXXX-1234
        - CREDIT_CARD: XXXX-XXXX-XXXX-1234
        - PAN: ABCP****4F
        - PHONE: +91-XXXXX-43210
        - EMAIL: h***l@domain.com
    """
    if not text:
        return "[REDACTED]"

    clean = text.strip()
    canonical = normalize_entity_type(entity_type)

    if canonical == "AADHAAR":
        digits = "".join(c for c in clean if c.isdigit())
        if len(digits) >= 4:
            return f"XXXX-XXXX-{digits[-4:]}"
        return "XXXX-XXXX-1234"

    elif canonical == "CREDIT_CARD":
        digits = "".join(c for c in clean if c.isdigit())
        if len(digits) >= 4:
            return f"XXXX-XXXX-XXXX-{digits[-4:]}"
        return "XXXX-XXXX-XXXX-0000"

    elif canonical == "PAN":
        pan_clean = clean.upper()
        if len(pan_clean) == 10:
            return f"{pan_clean[:4]}****{pan_clean[-2:]}"
        return f"{pan_clean[:2]}****{pan_clean[-1]}" if len(pan_clean) > 3 else "XXXXX1234X"

    elif canonical == "PHONE":
        digits = "".join(c for c in clean if c.isdigit())
        if len(digits) >= 4:
            if clean.startswith("+91"):
                return f"+91-XXXXX-{digits[-4:]}"
            return f"XXXXX-{digits[-4:]}"
        return "XXXXX-43210"

    elif canonical == "EMAIL":
        if "@" in clean:
            parts = clean.split("@", 1)
            local = parts[0]
            domain = parts[1]
            if len(local) > 2:
                masked_local = f"{local[0]}***{local[-1]}"
            elif len(local) == 2:
                masked_local = f"{local[0]}*"
            else:
                masked_local = "***"
            return f"{masked_local}@{domain}"
        return "u***@domain.com"

    elif canonical == "DATE_OF_BIRTH":
        if len(clean) >= 4:
            return f"**/**/{clean[-4:]}"
        return "**/**/****"

    elif canonical == "PERSON":
        words = clean.split()
        masked_words = []
        for w in words:
            if len(w) > 1:
                masked_words.append(f"{w[0]}" + "*" * (len(w) - 1))
            else:
                masked_words.append(f"{w}*")
        return " ".join(masked_words) if masked_words else "P*****"

    elif canonical == "ADDRESS":
        tokens = clean.split(",")
        if len(tokens) > 1:
            return f"Flat ***, ***, {tokens[-1].strip()}"
        if len(clean) > 8:
            return f"{clean[:4]}****{clean[-4:]}"
        return "****"

    else:
        # General fallback
        if len(clean) <= 4:
            return "****"
        return f"{clean[:2]}" + "*" * (len(clean) - 4) + f"{clean[-2:]}"


def format_location_str(loc: Any) -> str:
    """Format finding location descriptor for compact table display."""
    if not loc:
        return "Document"

    if isinstance(loc, dict):
        if loc.get("page") is not None:
            return f"Page {loc['page']}"
        if loc.get("cell") is not None:
            sheet = f"{loc.get('sheet_name')}:" if loc.get("sheet_name") else ""
            return f"{sheet}{loc['cell']}"
        if loc.get("paragraph_index") is not None:
            return f"Para {int(loc['paragraph_index']) + 1}"
        if loc.get("line") is not None:
            return f"Line {loc['line']}"
        if loc.get("start_char") is not None and loc.get("end_char") is not None:
            return f"Ch {loc['start_char']}-{loc['end_char']}"
    else:
        page = getattr(loc, "page", None)
        if page is not None:
            return f"Page {page}"
        cell = getattr(loc, "cell", None)
        if cell is not None:
            sheet = getattr(loc, "sheet_name", None)
            sheet_prefix = f"{sheet}:" if sheet else ""
            return f"{sheet_prefix}{cell}"
        para = getattr(loc, "paragraph_index", None)
        if para is not None:
            return f"Para {int(para) + 1}"
        line = getattr(loc, "line", None)
        if line is not None:
            return f"Line {line}"
        start = getattr(loc, "start_char", None)
        end = getattr(loc, "end_char", None)
        if start is not None and end is not None:
            return f"Ch {start}-{end}"

    return "Document"


def generate_pdf_report(
    scan_response: Optional[Union[ScanResponse, Dict[str, Any]]] = None,
    risk_score: Optional[int] = None,
    risk_level: Optional[str] = None,
    summary: Optional[Dict[str, Any]] = None,
    file_name: Optional[str] = None,
    file_type: Optional[str] = None,
    findings: Optional[List[Any]] = None,
) -> bytes:
    """Generate an enterprise-grade compliance audit PDF report.

    Args:
        scan_response: Optional ScanResponse or dict from document scan.
        risk_score: Optional risk score (0-100). Computed if omitted.
        risk_level: Optional risk level ('Low', 'Medium', 'High'). Computed if omitted.
        summary: Optional summary dictionary containing breakdown counts and verdict.
        file_name: Document name (extracted from scan_response if provided).
        file_type: Document extension (extracted from scan_response if provided).
        findings: List of Finding objects or dicts (extracted from scan_response if provided).

    Returns:
        Raw bytes of the generated PDF document.
    """
    # 1. Resolve parameters from scan_response if supplied
    if scan_response is not None:
        if isinstance(scan_response, dict):
            if file_name is None:
                file_name = scan_response.get("file_name", "document")
            if file_type is None:
                file_type = scan_response.get("file_type", "txt")
            if findings is None:
                findings = scan_response.get("findings", [])
        else:
            if file_name is None:
                file_name = getattr(scan_response, "file_name", "document")
            if file_type is None:
                file_type = getattr(scan_response, "file_type", "txt")
            if findings is None:
                findings = getattr(scan_response, "findings", [])

    file_name = file_name or "document"
    file_type = file_type or "txt"
    findings = findings or []

    # 2. Compute risk profile if not already supplied
    if risk_score is None or risk_level is None or summary is None:
        calc_score, calc_level, calc_summary = calculate_risk_profile(findings)
        risk_score = calc_score if risk_score is None else risk_score
        risk_level = calc_level if risk_level is None else risk_level
        summary = calc_summary if summary is None else summary

    if hasattr(summary, "model_dump"):
        summary_dict = summary.model_dump()
    elif isinstance(summary, dict):
        summary_dict = summary
    else:
        summary_dict = {
            "critical_count": getattr(summary, "critical_count", 0),
            "high_count": getattr(summary, "high_count", 0),
            "medium_count": getattr(summary, "medium_count", 0),
            "low_count": getattr(summary, "low_count", 0),
            "primary_threat": getattr(summary, "primary_threat", ""),
            "compliance_verdict": getattr(summary, "compliance_verdict", ""),
        }

    total_findings = len(findings)

    # 3. Establish document layout
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=46,
    )
    usable_width = 540  # 612 - 72

    # 4. Color Palette & Typography
    c_dark_slate = colors.HexColor("#0F172A")
    c_muted_slate = colors.HexColor("#475569")
    c_subtle_border = colors.HexColor("#E2E8F0")
    c_light_bg = colors.HexColor("#F8FAFC")

    if risk_level == "High":
        risk_text_color = colors.HexColor("#DC2626")
        risk_bg_color = colors.HexColor("#FEF2F2")
        risk_border_color = colors.HexColor("#FECACA")
        badge_label = "HIGH RISK"
    elif risk_level == "Medium":
        risk_text_color = colors.HexColor("#D97706")
        risk_bg_color = colors.HexColor("#FFFBEB")
        risk_border_color = colors.HexColor("#FDE68A")
        badge_label = "MEDIUM RISK"
    else:
        risk_text_color = colors.HexColor("#059669")
        risk_bg_color = colors.HexColor("#ECFDF5")
        risk_border_color = colors.HexColor("#A7F3D0")
        badge_label = "LOW RISK"

    # Styles
    styles = getSampleStyleSheet()

    style_title = ParagraphStyle(
        "AuditTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=colors.white,
    )

    style_subtitle = ParagraphStyle(
        "AuditSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#94A3B8"),
    )

    style_section_h = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=14,
        textColor=c_dark_slate,
        spaceBefore=10,
        spaceAfter=4,
    )

    style_body = ParagraphStyle(
        "BodySmall",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=c_dark_slate,
    )

    style_body_bold = ParagraphStyle(
        "BodySmallBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=11,
        textColor=c_dark_slate,
    )

    style_score_big = ParagraphStyle(
        "ScoreBig",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=26,
        leading=30,
        alignment=TA_CENTER,
        textColor=risk_text_color,
    )

    style_badge = ParagraphStyle(
        "BadgeText",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=11,
        alignment=TA_CENTER,
        textColor=risk_text_color,
    )

    style_th = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.white,
    )

    style_td = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9.5,
        textColor=c_dark_slate,
    )

    style_td_bold = ParagraphStyle(
        "TableCellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9.5,
        textColor=c_dark_slate,
    )

    style_reasoning = ParagraphStyle(
        "ReasoningCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=6.8,
        leading=8.5,
        textColor=c_muted_slate,
    )

    story = []

    # 5. Header Banner
    timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    audit_hash = hashlib.sha256(f"{file_name}_{timestamp_str}".encode()).hexdigest()[:10].upper()
    audit_id = f"SD-AUD-{audit_hash}"

    header_table_data = [
        [
            Paragraph("SENTINELDOC COMPLIANCE AUDIT REPORT", style_title),
            Paragraph(f"AUDIT ID: <b>{audit_id}</b>", ParagraphStyle(
                "AuditId",
                parent=style_subtitle,
                alignment=TA_RIGHT,
                textColor=colors.white,
                fontName="Helvetica-Bold",
            )),
        ],
        [
            Paragraph("Enterprise Document Privacy & Statutory Leak Detection Engine", style_subtitle),
            Paragraph(f"Generated: {timestamp_str}", ParagraphStyle(
                "GenTime",
                parent=style_subtitle,
                alignment=TA_RIGHT,
            )),
        ],
    ]

    header_table = Table(header_table_data, colWidths=[360, 180])
    header_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), c_dark_slate),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING", (0, 0), (-1, -1), 14),
            ("RIGHTPADDING", (0, 0), (-1, -1), 14),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )
    story.append(header_table)
    story.append(Spacer(1, 10))

    # 6. Executive Risk Summary Callout Box
    threat_text = summary_dict.get("primary_threat", "No severe threats detected.")
    verdict_text = summary_dict.get("compliance_verdict", "Compliant for distribution.")

    left_info = [
        Paragraph(f"<b>Document Name:</b> {file_name}", style_body),
        Spacer(1, 3),
        Paragraph(f"<b>Format:</b> {file_type.upper()} &nbsp;|&nbsp; <b>Total PII Findings:</b> {total_findings}", style_body),
        Spacer(1, 4),
        Paragraph(f"<b>Primary Threat:</b> {threat_text}", style_body),
        Spacer(1, 4),
        Paragraph(f"<b>Compliance Verdict:</b> {verdict_text}", style_body_bold),
    ]

    right_score = [
        Paragraph("OVERALL RISK SCORE", ParagraphStyle(
            "ScoreLabel",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9,
            alignment=TA_CENTER,
            textColor=c_muted_slate,
        )),
        Spacer(1, 2),
        Paragraph(f"{risk_score} / 100", style_score_big),
        Spacer(1, 4),
        Table(
            [[Paragraph(f"[ {badge_label} ]", style_badge)]],
            colWidths=[130],
            style=[
                ("BACKGROUND", (0, 0), (-1, -1), risk_bg_color),
                ("BOX", (0, 0), (-1, -1), 1, risk_border_color),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ],
        ),
    ]

    summary_box_data = [[left_info, right_score]]
    summary_box = Table(summary_box_data, colWidths=[370, 170])
    summary_box.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), c_light_bg),
            ("BOX", (0, 0), (-1, -1), 1, c_subtle_border),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )
    story.append(summary_box)
    story.append(Spacer(1, 8))

    # 7. Section 1: Severity Breakdown Table
    story.append(Paragraph("1. SEVERITY BREAKDOWN", style_section_h))

    c_crit = summary_dict.get("critical_count", 0)
    c_high = summary_dict.get("high_count", 0)
    c_med = summary_dict.get("medium_count", 0)
    c_low = summary_dict.get("low_count", 0)

    sev_table_data = [
        [
            Paragraph("Severity Tier", style_th),
            Paragraph("Governed Entity Classes", style_th),
            Paragraph("Findings Count", style_th),
            Paragraph("Required Compliance Action", style_th),
        ],
        [
            Paragraph("<b>Critical</b>", ParagraphStyle("Crit", parent=style_td, textColor=colors.HexColor("#DC2626"))),
            Paragraph("Aadhaar, Payment Cards", style_td),
            Paragraph(f"<b>{c_crit}</b>", style_td_bold),
            Paragraph("Immediate automated redaction required before external release", style_td),
        ],
        [
            Paragraph("<b>High</b>", ParagraphStyle("High", parent=style_td, textColor=colors.HexColor("#D97706"))),
            Paragraph("PAN, Date of Birth", style_td),
            Paragraph(f"<b>{c_high}</b>", style_td_bold),
            Paragraph("Mandatory privacy review and selective redaction", style_td),
        ],
        [
            Paragraph("<b>Medium</b>", ParagraphStyle("Med", parent=style_td, textColor=colors.HexColor("#B45309"))),
            Paragraph("Phone Number, Physical Address", style_td),
            Paragraph(f"<b>{c_med}</b>", style_td_bold),
            Paragraph("Verify external sharing consent and recipient authorization", style_td),
        ],
        [
            Paragraph("<b>Low</b>", ParagraphStyle("Low", parent=style_td, textColor=colors.HexColor("#059669"))),
            Paragraph("Email Address, Person Name, Other", style_td),
            Paragraph(f"<b>{c_low}</b>", style_td_bold),
            Paragraph("Standard enterprise data governance handling", style_td),
        ],
    ]

    sev_table = Table(sev_table_data, colWidths=[80, 160, 80, 220])
    sev_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), c_dark_slate),
            ("BOX", (0, 0), (-1, -1), 0.5, c_subtle_border),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, c_subtle_border),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )
    story.append(sev_table)
    story.append(Spacer(1, 8))

    # 8. Section 2: Entity Breakdown Table
    story.append(Paragraph("2. ENTITY BREAKDOWN MATRIX", style_section_h))

    if total_findings == 0:
        clean_callout_data = [
            [
                Paragraph(
                    "<b>CLEAN COMPLIANCE AUDIT:</b> Zero sensitive personal data entities detected. "
                    "Document conforms to safe-harbor standards and is approved for external distribution.",
                    ParagraphStyle(
                        "CleanCallout",
                        parent=style_body,
                        textColor=colors.HexColor("#065F46"),
                        alignment=TA_CENTER,
                    ),
                )
            ]
        ]
        clean_box = Table(clean_callout_data, colWidths=[usable_width])
        clean_box.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ECFDF5")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#A7F3D0")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ])
        )
        story.append(clean_box)
        story.append(Spacer(1, 8))
    else:
        # Aggregate by entity type
        entity_stats: Dict[str, Dict[str, Any]] = {}
        for f in findings:
            raw_t = f.get("entity_type") if isinstance(f, dict) else getattr(f, "entity_type", "UNKNOWN")
            conf = float(f.get("confidence") if isinstance(f, dict) else getattr(f, "confidence", 1.0))
            canonical = normalize_entity_type(raw_t)

            if canonical not in entity_stats:
                entity_stats[canonical] = {
                    "count": 0,
                    "conf_sum": 0.0,
                    "severity": get_entity_severity(canonical),
                }
            entity_stats[canonical]["count"] += 1
            entity_stats[canonical]["conf_sum"] += conf

        # Sort: Critical -> High -> Medium -> Low
        tier_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
        sorted_entities = sorted(
            entity_stats.items(),
            key=lambda item: (tier_order.get(item[1]["severity"], 4), -item[1]["count"]),
        )

        ent_table_data = [
            [
                Paragraph("Entity Type", style_th),
                Paragraph("Severity", style_th),
                Paragraph("Detections", style_th),
                Paragraph("Avg. Confidence", style_th),
                Paragraph("Remediation Status", style_th),
            ]
        ]

        for ent_name, data in sorted_entities:
            avg_conf = (data["conf_sum"] / data["count"]) * 100.0 if data["count"] > 0 else 0.0
            sev = data["severity"]

            if sev == "Critical":
                sev_color = colors.HexColor("#DC2626")
                status = "<b>REDACT (MANDATORY)</b>"
            elif sev == "High":
                sev_color = colors.HexColor("#D97706")
                status = "<b>REDACT (RECOMMENDED)</b>"
            elif sev == "Medium":
                sev_color = colors.HexColor("#B45309")
                status = "Review & Verify"
            else:
                sev_color = colors.HexColor("#059669")
                status = "Low Exposure"

            ent_table_data.append([
                Paragraph(f"<b>{ent_name}</b>", style_td),
                Paragraph(f"<b>{sev}</b>", ParagraphStyle("SevCol", parent=style_td, textColor=sev_color)),
                Paragraph(str(data["count"]), style_td),
                Paragraph(f"{avg_conf:.1f}%", style_td),
                Paragraph(status, style_td),
            ])

        ent_table = Table(ent_table_data, colWidths=[130, 80, 70, 90, 170])
        ent_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), c_dark_slate),
                ("BOX", (0, 0), (-1, -1), 0.5, c_subtle_border),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, c_subtle_border),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ])
        )
        story.append(ent_table)
        story.append(Spacer(1, 8))

    # 9. Section 3: Detailed Findings Audit Log
    story.append(Paragraph("3. DETAILED FINDINGS AUDIT LOG", style_section_h))

    if total_findings == 0:
        story.append(Paragraph("<i>No finding records to display. Document is free of detected personal data.</i>", style_body))
    else:
        # Table columns: ID (35), Location (65), Entity Type (80), Confidence (45), Masked Value (105), Reasoning (210) = 540
        findings_table_data = [
            [
                Paragraph("ID", style_th),
                Paragraph("Location", style_th),
                Paragraph("Entity Type", style_th),
                Paragraph("Conf.", style_th),
                Paragraph("Masked Value", style_th),
                Paragraph("Detection Reasoning", style_th),
            ]
        ]

        for idx, f in enumerate(findings, start=1):
            if isinstance(f, dict):
                f_id = f.get("id", f"find_{idx}")
                f_type = f.get("entity_type", "UNKNOWN")
                f_text = f.get("matched_text", "")
                f_conf = float(f.get("confidence", 1.0))
                f_reason = f.get("reasoning", "")
                f_loc = f.get("location")
            else:
                f_id = getattr(f, "id", f"find_{idx}")
                f_type = getattr(f, "entity_type", "UNKNOWN")
                f_text = getattr(f, "matched_text", "")
                f_conf = float(getattr(f, "confidence", 1.0))
                f_reason = getattr(f, "reasoning", "")
                f_loc = getattr(f, "location", None)

            masked_str = mask_pii(f_text, f_type)
            loc_str = format_location_str(f_loc)
            conf_str = f"{f_conf * 100.0:.0f}%"

            findings_table_data.append([
                Paragraph(f_id, style_td),
                Paragraph(loc_str, style_td),
                Paragraph(f"<b>{f_type}</b>", style_td),
                Paragraph(conf_str, style_td),
                Paragraph(f"<font name='Courier'>{masked_str}</font>", style_td),
                Paragraph(f_reason, style_reasoning),
            ])

        findings_table = Table(
            findings_table_data,
            colWidths=[35, 65, 80, 45, 105, 210],
            repeatRows=1,
        )

        table_styles = [
            ("BACKGROUND", (0, 0), (-1, 0), c_dark_slate),
            ("BOX", (0, 0), (-1, -1), 0.5, c_subtle_border),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, c_subtle_border),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]

        # Alternating row colors
        for row_idx in range(1, len(findings_table_data)):
            if row_idx % 2 == 0:
                table_styles.append(("BACKGROUND", (0, row_idx), (-1, row_idx), colors.HexColor("#F8FAFC")))

        findings_table.setStyle(TableStyle(table_styles))
        story.append(findings_table)

    # 10. Build PDF with NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes

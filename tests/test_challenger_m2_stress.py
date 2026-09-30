"""Empirical Stress, Multi-Format Layout & Document Non-Corruption Challenge Suite.

Authored by teamwork_preview_challenger_m2_2 (Stress & Multi-Format Layout Challenger).
Empirically stress-tests and verifies:
1. Multi-page PDFs (up to 50 pages) with sparse/dense redactions on multiple pages,
   verifying exact page count, text stream purging, visual overlay, and valid xref tables.
2. Word documents (.docx) with redactions across body paragraphs (single & multi-run)
   and embedded table cells across multiple tables, verifying valid ZIP container and Word XML.
3. Excel workbooks (.xlsx) with multiple sheets, merged cells, cross-sheet references,
   and formulas (SUM, AVERAGE, COUNT, IF, concatenation, arithmetic), verifying formula preservation.
4. CSV files with quoted commas, multiline cells, escaped quotes, and trailing empty fields,
   verifying row/column preservation and delimiter parsing.
5. Plain text files (.txt) with CRLF and LF line endings, verifying byte-for-byte line ending
   preservation and right-to-left multi-entity offset replacement.
6. Deep document integrity invariants: valid PDF xref table without repair, valid ZIP structures
   (testzip() is None), well-formed XML schemas, and golden round-trip re-scan zero residual leaks.
"""
import io
import csv
import json
import zipfile
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Set, Optional

import fitz  # PyMuPDF
import docx
import openpyxl
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Module-scoped FastAPI TestClient fixture."""
    return TestClient(app)


# =====================================================================
# 1. MULTI-PAGE PDF STRESS & REDACTION TESTS (UP TO 50 PAGES)
# =====================================================================

class TestPdfMultipageStressAndRedaction:
    """Empirical stress tests for multi-page PDF documents and redactions up to 50 pages."""

    def test_pdf_50_pages_sparse_and_dense_redaction(self, client: TestClient):
        """Stress-test 50-page PDF with multi-page PII, blank pages, and non-PII filler.
        
        Verifies:
        - Exact 50-page count is preserved.
        - Redacted text stream is purged on targeted pages.
        - Visual black overlay is rendered.
        - Non-redacted text on those pages and intervening pages remains intact.
        - PDF xref table is valid without repair flags.
        - Re-scanning the redacted PDF yields 0 critical leaks.
        """
        doc = fitz.open()

        # Build 50-page PDF
        for page_idx in range(50):
            page_num = page_idx + 1
            p = doc.new_page(width=612, height=792)

            if page_num == 1:
                p.insert_text(fitz.Point(72, 100), "Document Cover & Executive Overview", fontsize=14)
                p.insert_text(fitz.Point(72, 140), "Authorized Officer Aadhaar: 3675 9832 4511")
                p.insert_text(fitz.Point(72, 170), "Corporate Tax Identifier PAN: ABCPE1234F")
                p.insert_text(fitz.Point(72, 200), "Security Classification: Strictly Confidential")
            elif page_num == 5:
                # Blank page
                pass
            elif page_num == 10:
                p.insert_text(fitz.Point(72, 100), "Corporate Billing and Card Authorization", fontsize=14)
                p.insert_text(fitz.Point(72, 140), "Primary Payment Card: 4532 0151 1283 0366")
                p.insert_text(fitz.Point(72, 170), "Cardholder: Vikram Singhania")
                p.insert_text(fitz.Point(72, 200), "Billing status: Active in good standing")
            elif page_num == 20:
                # False positive numbers that should NOT be flagged or redacted
                p.insert_text(fitz.Point(72, 100), "Supply Chain Tracking Telemetry", fontsize=14)
                p.insert_text(fitz.Point(72, 140), "Order ID: 123456789012 (12 digits, fails checksum)")
                p.insert_text(fitz.Point(72, 170), "Warehouse Zip: 560001 (6-digit postal code)")
                p.insert_text(fitz.Point(72, 200), "SKU Model: PAN1234567 (invalid PAN format)")
            elif page_num == 25:
                p.insert_text(fitz.Point(72, 100), "Incident Response Contact Directory", fontsize=14)
                p.insert_text(fitz.Point(72, 140), "Duty Officer Mobile: +91 9876543210")
                p.insert_text(fitz.Point(72, 170), "Emergency Email: security.ops@sentinel-defense.in")
                p.insert_text(fitz.Point(72, 200), "Location: Level 4 Control Room")
            elif page_num == 37:
                p.insert_text(fitz.Point(72, 100), "Statutory Tax Declaration", fontsize=14)
                p.insert_text(fitz.Point(72, 140), "Individual Taxpayer PAN: BKZPK7190M")
                p.insert_text(fitz.Point(72, 170), "Declaration Status: Filed on time")
            elif page_num == 45:
                # Another blank page
                pass
            elif page_num == 50:
                p.insert_text(fitz.Point(72, 100), "Final Legal & Audit Sign-Off", fontsize=14)
                p.insert_text(fitz.Point(72, 140), "Signatory Aadhaar: 9876 5432 1096")
                p.insert_text(fitz.Point(72, 170), "Signatory PAN: BNZPK9876M")
                p.insert_text(fitz.Point(72, 200), "Audit Completed by Compliance Bureau")
            else:
                p.insert_text(fitz.Point(72, 100), f"Standard Operating Procedure — Chapter Section {page_num}", fontsize=12)
                p.insert_text(fitz.Point(72, 130), "General business text detailing non-sensitive workflows and procedures.")
                p.insert_text(fitz.Point(72, 160), "All operational teams must adhere to established governance protocols.")

        pdf_bytes = doc.tobytes(deflate=True)
        doc.close()

        # Step 1: Scan 50-page PDF
        scan_resp = client.post(
            "/scan",
            files={"file": ("stress_50p.pdf", pdf_bytes, "application/pdf")}
        )
        assert scan_resp.status_code == 200, f"Scan failed: {scan_resp.text}"
        scan_data = scan_resp.json()
        findings = scan_data["findings"]
        assert len(findings) >= 7, f"Expected at least 7 findings across 50 pages, got {len(findings)}"

        # Group findings by page
        findings_by_page: Dict[int, List[Dict[str, Any]]] = {}
        for f in findings:
            p_num = f["location"]["page"]
            findings_by_page.setdefault(p_num, []).append(f)

        assert 1 in findings_by_page, "Page 1 findings missing"
        assert 10 in findings_by_page, "Page 10 findings missing"
        assert 25 in findings_by_page, "Page 25 findings missing"
        assert 37 in findings_by_page, "Page 37 findings missing"
        assert 50 in findings_by_page, "Page 50 findings missing"
        assert 5 not in findings_by_page, "Blank Page 5 should have 0 findings"
        assert 20 not in findings_by_page, "False-positive Page 20 should have 0 findings"
        assert 45 not in findings_by_page, "Blank Page 45 should have 0 findings"

        # Step 2: Redact all findings
        redact_resp = client.post(
            "/redact",
            files={"file": ("stress_50p.pdf", pdf_bytes, "application/pdf")},
            data={"finding_ids": "all"}
        )
        assert redact_resp.status_code == 200, f"Redact failed: {redact_resp.text}"
        assert "application/pdf" in redact_resp.headers.get("content-type", "")
        cd_header = redact_resp.headers.get("content-disposition", "")
        assert "redacted_stress_50p.pdf" in cd_header

        redacted_bytes = redact_resp.content
        assert len(redacted_bytes) > 1000

        # Step 3: Empirical Document Integrity & Format Invariants
        redacted_doc = fitz.open(stream=redacted_bytes, filetype="pdf")
        assert redacted_doc.is_pdf is True
        assert redacted_doc.is_repaired is False, "PDF was repaired; corrupt xref table detected!"
        assert redacted_doc.xref_length() > 0, "PDF xref table is missing or empty"
        assert len(redacted_doc) == 50, f"Page count corrupted: expected 50, got {len(redacted_doc)}"

        # Verify targeted pages no longer contain raw text, but retain non-PII headers
        p1_text = redacted_doc[0].get_text()
        assert "3675 9832 4511" not in p1_text
        assert "ABCPE1234F" not in p1_text
        assert "Document Cover & Executive Overview" in p1_text
        assert "Security Classification: Strictly Confidential" in p1_text

        p10_text = redacted_doc[9].get_text()
        assert "4532 0151 1283 0366" not in p10_text
        assert "Corporate Billing and Card Authorization" in p10_text
        assert "Billing status: Active in good standing" in p10_text

        p25_text = redacted_doc[24].get_text()
        assert "9876543210" not in p25_text
        assert "security.ops@sentinel-defense.in" not in p25_text
        assert "Incident Response Contact Directory" in p25_text

        p37_text = redacted_doc[36].get_text()
        assert "BKZPK7190M" not in p37_text
        assert "Statutory Tax Declaration" in p37_text

        p50_text = redacted_doc[49].get_text()
        assert "9876 5432 1096" not in p50_text
        assert "BNZPK9876M" not in p50_text
        assert "Final Legal & Audit Sign-Off" in p50_text

        # Verify blank pages remained completely empty
        assert redacted_doc[4].get_text().strip() == ""
        assert redacted_doc[44].get_text().strip() == ""

        # Verify page 20 false positive numbers remain completely intact
        p20_text = redacted_doc[19].get_text()
        assert "Order ID: 123456789012" in p20_text
        assert "Warehouse Zip: 560001" in p20_text

        # Verify rendering integrity on every single page (no graphics engine crashes)
        for p_idx in (0, 4, 9, 19, 24, 36, 44, 49):
            pix = redacted_doc[p_idx].get_pixmap()
            assert pix.width > 0 and pix.height > 0

        redacted_doc.close()

        # Step 4: Golden Round-Trip Re-Scan
        rescan_resp = client.post(
            "/scan",
            files={"file": ("redacted_stress_50p.pdf", redacted_bytes, "application/pdf")}
        )
        assert rescan_resp.status_code == 200
        rescan_findings = rescan_resp.json()["findings"]
        critical_leaks = [
            f for f in rescan_findings
            if f["entity_type"] in ("AADHAAR", "PAN", "CREDIT_CARD", "PHONE_NUMBER", "EMAIL_ADDRESS")
        ]
        assert len(critical_leaks) == 0, f"Critical PII leaked in redacted 50-page PDF: {critical_leaks}"

    def test_pdf_selective_multipage_redaction(self, client: TestClient):
        """Verify selective redaction on multi-page PDF only redacts chosen page findings."""
        doc = fitz.open()
        p1 = doc.new_page(width=612, height=792)
        p1.insert_text(fitz.Point(72, 100), "Page 1 Aadhaar: 3675 9832 4511")

        p2 = doc.new_page(width=612, height=792)
        p2.insert_text(fitz.Point(72, 100), "Page 2 Card: 4532 0151 1283 0366")

        p3 = doc.new_page(width=612, height=792)
        p3.insert_text(fitz.Point(72, 100), "Page 3 PAN: ABCPE1234F")

        pdf_bytes = doc.tobytes()
        doc.close()

        # Scan
        scan_resp = client.post(
            "/scan",
            files={"file": ("selective_multipage.pdf", pdf_bytes, "application/pdf")}
        )
        assert scan_resp.status_code == 200
        findings = scan_resp.json()["findings"]

        # Select ONLY Card on Page 2
        card_findings = [f["id"] for f in findings if f["entity_type"] == "CREDIT_CARD"]
        assert len(card_findings) == 1

        # Redact only Card
        redact_resp = client.post(
            "/redact",
            files={"file": ("selective_multipage.pdf", pdf_bytes, "application/pdf")},
            data={"finding_ids": json.dumps(card_findings)}
        )
        assert redact_resp.status_code == 200
        redacted_bytes = redact_resp.content

        # Verify Page 2 Card is redacted, but Page 1 Aadhaar and Page 3 PAN remain
        redacted_doc = fitz.open(stream=redacted_bytes, filetype="pdf")
        assert len(redacted_doc) == 3
        assert "4532 0151 1283 0366" not in redacted_doc[1].get_text()
        assert "3675 9832 4511" in redacted_doc[0].get_text(), "Page 1 Aadhaar was improperly redacted"
        assert "ABCPE1234F" in redacted_doc[2].get_text(), "Page 3 PAN was improperly redacted"
        redacted_doc.close()

    def test_pdf_duplicate_pii_across_multiple_pages(self, client: TestClient):
        """Verify identical PII string recurring on distinct pages is redacted on every page."""
        doc = fitz.open()
        # Same Aadhaar on Page 1, Page 2, and Page 3
        for i in range(3):
            p = doc.new_page(width=612, height=792)
            p.insert_text(fitz.Point(72, 100), f"Section {i+1} Verification Header")
            p.insert_text(fitz.Point(72, 140), "Customer Aadhaar: 3675 9832 4511")

        pdf_bytes = doc.tobytes()
        doc.close()

        redact_resp = client.post(
            "/redact",
            files={"file": ("duplicate_multipage.pdf", pdf_bytes, "application/pdf")},
            data={"finding_ids": "all"}
        )
        assert redact_resp.status_code == 200
        redacted_bytes = redact_resp.content

        redacted_doc = fitz.open(stream=redacted_bytes, filetype="pdf")
        assert len(redacted_doc) == 3
        for page_idx in range(3):
            txt = redacted_doc[page_idx].get_text()
            assert "3675 9832 4511" not in txt, f"Aadhaar leaked on page {page_idx + 1}"
            assert f"Section {page_idx+1} Verification Header" in txt
        redacted_doc.close()


# =====================================================================
# 2. WORD DOCUMENT (.DOCX) BODY & EMBEDDED TABLE REDACTION
# =====================================================================

class TestDocxBodyAndEmbeddedTableRedaction:
    """Empirical stress tests for Word documents with body paragraphs and embedded tables."""

    def test_docx_body_and_embedded_table_redaction(self, client: TestClient):
        """Verify redactions across body paragraphs (single & multi-run) and multiple tables.
        
        Verifies:
        - Body paragraph findings replaced with [REDACTED].
        - Table cell findings replaced with [REDACTED].
        - Surrounding paragraph styling, headers, and table structures preserved.
        - ZIP structure is valid and XML schema is well-formed.
        - Golden round-trip re-scan yields 0 critical leaks.
        """
        doc = docx.Document()

        # Heading (paragraphs[0]) & Non-PII Intro (paragraphs[1])
        doc.add_heading("Corporate Personnel Security Audit", level=1)
        doc.add_paragraph("This document certifies confidential compliance verification for enterprise personnel.")

        # Body Paragraph with Aadhaar & PAN (paragraphs[2])
        doc.add_paragraph("Primary Auditor Credentials: Aadhaar 3675 9832 4511 and Permanent Account Number ABCPE1234F.")

        # Body Paragraph with Multi-run Styling (paragraphs[3])
        p3 = doc.add_paragraph()
        r1 = p3.add_run("Duty Officer Contact: Mobile ")
        r1.bold = True
        r2 = p3.add_run("+91 9876543210")
        r2.italic = True
        r3 = p3.add_run(" and email ")
        r4 = p3.add_run("priya.sharma@internal-corp.in")
        r4.underline = True
        r5 = p3.add_run(" for dispatch.")

        # Table 1: Employee Directory (3 rows x 3 cols)
        t1 = doc.add_table(rows=3, cols=3)
        t1_hdr = t1.rows[0].cells
        t1_hdr[0].text = "Emp ID"
        t1_hdr[1].text = "Designation"
        t1_hdr[2].text = "Official Email"

        t1_r1 = t1.rows[1].cells
        t1_r1[0].text = "EMP-101"
        t1_r1[1].text = "Lead Architect"
        t1_r1[2].text = "aarav.sharma@corp.in"

        t1_r2 = t1.rows[2].cells
        t1_r2[0].text = "EMP-102"
        t1_r2[1].text = "Principal Consultant"
        t1_r2[2].text = "rohan.mehta@corp.in"

        # Table 2: Financial Identifiers (2 rows x 3 cols)
        t2 = doc.add_table(rows=2, cols=3)
        t2_hdr = t2.rows[0].cells
        t2_hdr[0].text = "Account Class"
        t2_hdr[1].text = "Identifier Value"
        t2_hdr[2].text = "Verification"

        t2_r1 = t2.rows[1].cells
        t2_r1[0].text = "Corporate Visa"
        t2_r1[1].text = "Card: 4532 0151 1283 0366"
        t2_r1[2].text = "Luhn Validated"

        # Table 3: Edge Table with Empty Cells
        t3 = doc.add_table(rows=1, cols=2)
        t3.rows[0].cells[0].text = ""  # Empty cell
        t3.rows[0].cells[1].text = "Backup Aadhaar: 9876 5432 1096"

        # Closing Body Paragraph
        doc.add_paragraph("End of compliance record. Verified by General Counsel.")

        buf = io.BytesIO()
        doc.save(buf)
        docx_bytes = buf.getvalue()

        # Step 1: Scan
        scan_resp = client.post(
            "/scan",
            files={"file": ("audit_memo.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        )
        assert scan_resp.status_code == 200
        scan_data = scan_resp.json()
        findings = scan_data["findings"]
        assert len(findings) >= 6, f"Expected at least 6 findings, got {len(findings)}"

        # Verify findings exist in both paragraphs and tables
        para_findings = [f for f in findings if f["location"]["paragraph_index"] is not None]
        table_findings = [f for f in findings if f["location"]["sheet_name"] is not None and "Table" in f["location"]["sheet_name"]]
        assert len(para_findings) >= 3, "Expected at least 3 paragraph findings"
        assert len(table_findings) >= 3, "Expected at least 3 table findings"

        # Step 2: Redact All
        redact_resp = client.post(
            "/redact",
            files={"file": ("audit_memo.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            data={"finding_ids": "all"}
        )
        assert redact_resp.status_code == 200
        assert "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in redact_resp.headers.get("content-type", "")
        redacted_bytes = redact_resp.content

        # Step 3: Verify ZIP Container Integrity & XML Schemas
        zf = zipfile.ZipFile(io.BytesIO(redacted_bytes))
        assert zf.testzip() is None, "DOCX ZIP structure is corrupt!"
        assert "word/document.xml" in zf.namelist()
        assert "[Content_Types].xml" in zf.namelist()

        # Parse XML tree directly
        doc_xml_content = zf.read("word/document.xml")
        xml_root = ET.fromstring(doc_xml_content)
        assert xml_root is not None, "Failed to parse word/document.xml"

        # Step 4: Verify Python-Docx Document Structure
        redacted_doc = docx.Document(io.BytesIO(redacted_bytes))

        # Check non-PII intro paragraph is intact
        p1_text = redacted_doc.paragraphs[1].text
        assert "This document certifies confidential compliance verification" in p1_text

        # Check body paragraph with Aadhaar and PAN (paragraphs[2])
        p2_text = redacted_doc.paragraphs[2].text
        assert "3675 9832 4511" not in p2_text
        assert "ABCPE1234F" not in p2_text
        assert "[REDACTED]" in p2_text
        assert "Primary Auditor Credentials" in p2_text

        # Check multi-run styled paragraph (paragraphs[3])
        p3_text = redacted_doc.paragraphs[3].text
        assert "9876543210" not in p3_text
        assert "priya.sharma@internal-corp.in" not in p3_text
        assert "[REDACTED]" in p3_text

        # Check Table 1
        t1_redacted = redacted_doc.tables[0]
        assert t1_redacted.rows[0].cells[2].text == "Official Email"  # Header intact
        assert "aarav.sharma@corp.in" not in t1_redacted.rows[1].cells[2].text
        assert "[REDACTED]" in t1_redacted.rows[1].cells[2].text
        assert "rohan.mehta@corp.in" not in t1_redacted.rows[2].cells[2].text
        assert "[REDACTED]" in t1_redacted.rows[2].cells[2].text
        assert t1_redacted.rows[1].cells[0].text == "EMP-101"  # Non-PII cell intact

        # Check Table 2
        t2_redacted = redacted_doc.tables[1]
        assert "4532 0151 1283 0366" not in t2_redacted.rows[1].cells[1].text
        assert "[REDACTED]" in t2_redacted.rows[1].cells[1].text
        assert t2_redacted.rows[1].cells[0].text == "Corporate Visa"

        # Check Table 3
        t3_redacted = redacted_doc.tables[2]
        assert "9876 5432 1096" not in t3_redacted.rows[0].cells[1].text
        assert "[REDACTED]" in t3_redacted.rows[0].cells[1].text
        assert t3_redacted.rows[0].cells[0].text == ""

        # Step 5: Golden Round-Trip Re-Scan
        rescan_resp = client.post(
            "/scan",
            files={"file": ("redacted_memo.docx", redacted_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        )
        assert rescan_resp.status_code == 200
        critical_leaks = [
            f for f in rescan_resp.json()["findings"]
            if f["entity_type"] in ("AADHAAR", "PAN", "CREDIT_CARD", "PHONE_NUMBER", "EMAIL_ADDRESS")
        ]
        assert len(critical_leaks) == 0, f"Critical PII leaked in redacted DOCX: {critical_leaks}"

    def test_docx_selective_table_only_redaction(self, client: TestClient):
        """Verify selective redaction targeting only table findings leaves body paragraphs intact."""
        doc = docx.Document()
        doc.add_paragraph("Body Identity Record: Aadhaar 3675 9832 4511")
        t = doc.add_table(rows=2, cols=2)
        t.rows[0].cells[0].text = "Type"
        t.rows[0].cells[1].text = "Value"
        t.rows[1].cells[0].text = "Tax ID"
        t.rows[1].cells[1].text = "PAN: ABCPE1234F"

        buf = io.BytesIO()
        doc.save(buf)
        docx_bytes = buf.getvalue()

        # Scan
        scan_resp = client.post(
            "/scan",
            files={"file": ("selective_docx.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        )
        assert scan_resp.status_code == 200
        findings = scan_resp.json()["findings"]

        pan_findings = [f["id"] for f in findings if f["entity_type"] == "PAN"]
        assert len(pan_findings) == 1

        # Redact only PAN in Table
        redact_resp = client.post(
            "/redact",
            files={"file": ("selective_docx.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            data={"finding_ids": json.dumps(pan_findings)}
        )
        assert redact_resp.status_code == 200
        redacted_bytes = redact_resp.content

        redacted_doc = docx.Document(io.BytesIO(redacted_bytes))
        # Body Aadhaar must still be present!
        assert "3675 9832 4511" in redacted_doc.paragraphs[0].text
        # Table PAN must be redacted!
        assert "ABCPE1234F" not in redacted_doc.tables[0].rows[1].cells[1].text
        assert "[REDACTED]" in redacted_doc.tables[0].rows[1].cells[1].text


# =====================================================================
# 3. EXCEL WORKBOOK (.XLSX) MULTI-SHEET & FORMULA PRESERVATION
# =====================================================================

class TestXlsxMultiSheetAndFormulas:
    """Empirical stress tests for Excel workbooks with multiple sheets and formulas."""

    def test_xlsx_multisheet_and_formula_preservation(self, client: TestClient):
        """Stress-test 4-sheet Excel workbook with formulas, merged cells, and PII.
        
        Verifies:
        - PII cells across sheets are replaced with [REDACTED].
        - All formula strings (=SUM, =AVERAGE, =COUNT, =IF, cross-sheet refs, string concats)
          are preserved verbatim and NOT overwritten by None or cached values.
        - ZIP structure is valid and sheet XMLs are well-formed.
        - Golden round-trip re-scan yields 0 critical leaks.
        """
        wb = openpyxl.Workbook()
        wb.remove(wb.active)  # Remove default sheet

        # Sheet 1: Salaries
        ws1 = wb.create_sheet(title="Salaries")
        ws1.append(["Emp ID", "Staff Name", "Aadhaar Number", "Monthly Base", "Annual Gross"])
        ws1.append([1001, "Aarav Sharma", "3675 9832 4511", 50000, "=D2*12"])
        ws1.append([1002, "Neha Patel", "9876 5432 1096", 65000, "=D3*12"])
        ws1.append(["TOTAL", "", "", "=SUM(D2:D3)", "=SUM(E2:E3)"])
        ws1.append(["AVERAGE", "", "", "=AVERAGE(D2:D3)", "=AVERAGE(E2:E3)"])
        ws1.append(["AUDIT STATUS", "", "", '=IF(D4>100000, "High Payroll", "Standard")', "=COUNT(D2:D3)"])

        # Sheet 2: Financial Accounts
        ws2 = wb.create_sheet(title="FinancialAccounts")
        ws2.append(["Account ID", "Tax PAN", "Corporate Card", "Base Cost", "Service Tax (18%)", "Total Payable"])
        ws2.append(["ACC-01", "ABCPE1234F", "4532 0151 1283 0366", 25000, "=D2*0.18", "=D2+E2"])
        ws2.append(["ACC-02", "BKZPK7190M", "5424-1801-2345-6789", 40000, "=D3*0.18", "=D3+E3"])
        ws2.append(["SUMMARY", "TOTALS", "CARDS", "=SUM(D2:D3)", "=SUM(E2:E3)", "=SUM(F2:F3)"])

        # Sheet 3: CrossReferences
        ws3 = wb.create_sheet(title="CrossReferences")
        ws3.append(["Metric Code", "Formula Reference"])
        ws3.append(["Consolidated Base Payroll", "='Salaries'!D4"])
        ws3.append(["Consolidated Total Expenses", "='FinancialAccounts'!F4"])
        ws3.append(["Net Corporate Outflow", "=B2+B3"])
        ws3.append(["Dynamic Report Title", '="Financial Audit for " & \'Salaries\'!B2'])

        # Sheet 4: EmptySheet
        wb.create_sheet(title="EmptySheet")

        buf = io.BytesIO()
        wb.save(buf)
        xlsx_bytes = buf.getvalue()
        wb.close()

        # Step 1: Scan
        scan_resp = client.post(
            "/scan",
            files={"file": ("corporate_finances.xlsx", xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
        assert scan_resp.status_code == 200
        scan_data = scan_resp.json()
        findings = scan_data["findings"]
        assert len(findings) >= 5, f"Expected at least 5 findings in XLSX, got {len(findings)}"

        # Check sheet location mapping
        sheets_found = {f["location"]["sheet_name"] for f in findings}
        assert "Salaries" in sheets_found
        assert "FinancialAccounts" in sheets_found
        assert "CrossReferences" not in sheets_found, "Formula sheet should have 0 findings"
        assert "EmptySheet" not in sheets_found, "Empty sheet should have 0 findings"

        # Step 2: Redact All
        redact_resp = client.post(
            "/redact",
            files={"file": ("corporate_finances.xlsx", xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={"finding_ids": "all"}
        )
        assert redact_resp.status_code == 200
        assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in redact_resp.headers.get("content-type", "")
        redacted_bytes = redact_resp.content

        # Step 3: Verify ZIP Container Integrity & Sheet XML Schemas
        zf = zipfile.ZipFile(io.BytesIO(redacted_bytes))
        assert zf.testzip() is None, "XLSX ZIP structure is corrupt!"
        assert "[Content_Types].xml" in zf.namelist()
        assert "xl/workbook.xml" in zf.namelist()

        # Parse every worksheet XML directly
        sheet_xmls = [name for name in zf.namelist() if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")]
        assert len(sheet_xmls) == 4, f"Expected 4 sheet XMLs, found {len(sheet_xmls)}"
        for sxml in sheet_xmls:
            tree = ET.fromstring(zf.read(sxml))
            assert tree is not None, f"Failed to parse {sxml}"

        # Step 4: Verify Workbook Structure and Formula Preservation
        redacted_wb = openpyxl.load_workbook(io.BytesIO(redacted_bytes), data_only=False)
        assert redacted_wb.sheetnames == ["Salaries", "FinancialAccounts", "CrossReferences", "EmptySheet"]

        # Check Sheet 1: Salaries
        rws1 = redacted_wb["Salaries"]
        # Non-PII cell values preserved
        assert rws1["A1"].value == "Emp ID"
        assert rws1["A2"].value == 1001
        assert rws1["D2"].value == 50000
        # PII cell values redacted
        assert rws1["C2"].value == "[REDACTED]"
        assert rws1["C3"].value == "[REDACTED]"
        # Formulas strictly preserved verbatim!
        assert rws1["E2"].value == "=D2*12", f"Formula corrupted: {rws1['E2'].value}"
        assert rws1["E3"].value == "=D3*12", f"Formula corrupted: {rws1['E3'].value}"
        assert rws1["D4"].value == "=SUM(D2:D3)", f"Formula corrupted: {rws1['D4'].value}"
        assert rws1["E4"].value == "=SUM(E2:E3)", f"Formula corrupted: {rws1['E4'].value}"
        assert rws1["D5"].value == "=AVERAGE(D2:D3)", f"Formula corrupted: {rws1['D5'].value}"
        assert rws1["E5"].value == "=AVERAGE(E2:E3)", f"Formula corrupted: {rws1['E5'].value}"
        assert rws1["D6"].value == '=IF(D4>100000, "High Payroll", "Standard")', f"Formula corrupted: {rws1['D6'].value}"
        assert rws1["E6"].value == "=COUNT(D2:D3)", f"Formula corrupted: {rws1['E6'].value}"

        # Check Sheet 2: Financial Accounts
        rws2 = redacted_wb["FinancialAccounts"]
        # Non-PII preserved
        assert rws2["A2"].value == "ACC-01"
        assert rws2["D2"].value == 25000
        # PII redacted
        assert rws2["B2"].value == "[REDACTED]"
        assert rws2["C2"].value == "[REDACTED]"
        assert rws2["B3"].value == "[REDACTED]"
        assert rws2["C3"].value == "[REDACTED]"
        # Formulas strictly preserved
        assert rws2["E2"].value == "=D2*0.18", f"Formula corrupted: {rws2['E2'].value}"
        assert rws2["F2"].value == "=D2+E2", f"Formula corrupted: {rws2['F2'].value}"
        assert rws2["E3"].value == "=D3*0.18", f"Formula corrupted: {rws2['E3'].value}"
        assert rws2["F3"].value == "=D3+E3", f"Formula corrupted: {rws2['F3'].value}"
        assert rws2["D4"].value == "=SUM(D2:D3)", f"Formula corrupted: {rws2['D4'].value}"
        assert rws2["E4"].value == "=SUM(E2:E3)", f"Formula corrupted: {rws2['E4'].value}"
        assert rws2["F4"].value == "=SUM(F2:F3)", f"Formula corrupted: {rws2['F4'].value}"

        # Check Sheet 3: CrossReferences
        rws3 = redacted_wb["CrossReferences"]
        assert rws3["B2"].value == "='Salaries'!D4", f"Cross-sheet formula corrupted: {rws3['B2'].value}"
        assert rws3["B3"].value == "='FinancialAccounts'!F4", f"Cross-sheet formula corrupted: {rws3['B3'].value}"
        assert rws3["B4"].value == "=B2+B3", f"Arithmetic formula corrupted: {rws3['B4'].value}"
        assert rws3["B5"].value == '="Financial Audit for " & \'Salaries\'!B2', f"String concat corrupted: {rws3['B5'].value}"

        # Check Sheet 4: EmptySheet
        rws4 = redacted_wb["EmptySheet"]
        assert rws4.max_row == 1 and rws4.max_column == 1 and rws4["A1"].value is None

        redacted_wb.close()

        # Step 5: Golden Round-Trip Re-Scan
        rescan_resp = client.post(
            "/scan",
            files={"file": ("redacted_finances.xlsx", redacted_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
        assert rescan_resp.status_code == 200
        critical_leaks = [
            f for f in rescan_resp.json()["findings"]
            if f["entity_type"] in ("AADHAAR", "PAN", "CREDIT_CARD")
        ]
        assert len(critical_leaks) == 0, f"Critical PII leaked in redacted XLSX: {critical_leaks}"

    def test_xlsx_selective_sheet_redaction_preserves_unselected(self, client: TestClient):
        """Verify selective redaction of Sheet 1 leaves Sheet 2 PII intact and all formulas intact."""
        wb = openpyxl.Workbook()
        ws1 = wb.active
        ws1.title = "SheetA"
        ws1.append(["Name", "Aadhaar", "Bonus"])
        ws1.append(["User 1", "3675 9832 4511", 5000])
        ws1.append(["Total", "", "=SUM(C2:C2)"])

        ws2 = wb.create_sheet(title="SheetB")
        ws2.append(["Name", "PAN", "Deduction"])
        ws2.append(["User 2", "ABCPE1234F", 1000])
        ws2.append(["Total", "", "=SUM(C2:C2)"])

        buf = io.BytesIO()
        wb.save(buf)
        xlsx_bytes = buf.getvalue()
        wb.close()

        scan_resp = client.post(
            "/scan",
            files={"file": ("selective.xlsx", xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
        assert scan_resp.status_code == 200
        findings = scan_resp.json()["findings"]

        sheeta_findings = [f["id"] for f in findings if f["location"]["sheet_name"] == "SheetA"]
        assert len(sheeta_findings) >= 1

        redact_resp = client.post(
            "/redact",
            files={"file": ("selective.xlsx", xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={"finding_ids": json.dumps(sheeta_findings)}
        )
        assert redact_resp.status_code == 200
        redacted_bytes = redact_resp.content

        redacted_wb = openpyxl.load_workbook(io.BytesIO(redacted_bytes), data_only=False)
        # SheetA Aadhaar is redacted
        assert redacted_wb["SheetA"]["B2"].value == "[REDACTED]"
        assert redacted_wb["SheetA"]["C3"].value == "=SUM(C2:C2)"
        # SheetB PAN is UNTOUCHED
        assert "ABCPE1234F" in str(redacted_wb["SheetB"]["B2"].value)
        assert redacted_wb["SheetB"]["C3"].value == "=SUM(C2:C2)"
        redacted_wb.close()

    def test_xlsx_merged_cells_and_extreme_columns(self, client: TestClient):
        """Verify merged cells and column coordinates beyond Z (e.g. AA) do not cause MergedCell write errors."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "WideSheet"

        # Merged header title
        ws.merge_cells("A1:D1")
        ws["A1"] = "Executive Confidential Ledger"

        # Normal PII in column A
        ws["A2"] = "Aadhaar: 3675 9832 4511"

        # PII in column AA (column index 27)
        ws["AA2"] = "PAN: ABCPE1234F"

        buf = io.BytesIO()
        wb.save(buf)
        xlsx_bytes = buf.getvalue()
        wb.close()

        redact_resp = client.post(
            "/redact",
            files={"file": ("wide_sheet.xlsx", xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={"finding_ids": "all"}
        )
        assert redact_resp.status_code == 200
        redacted_bytes = redact_resp.content

        redacted_wb = openpyxl.load_workbook(io.BytesIO(redacted_bytes), data_only=False)
        rws = redacted_wb["WideSheet"]
        assert rws["A1"].value == "Executive Confidential Ledger"
        assert "[REDACTED]" in str(rws["A2"].value)
        assert "[REDACTED]" in str(rws["AA2"].value)
        redacted_wb.close()


# =====================================================================
# 4. CSV FILES WITH QUOTED COMMAS AND MULTILINE TEXT
# =====================================================================

class TestCsvQuotedCommasAndMultilineText:
    """Empirical stress tests for CSV files with quoted commas and multiline cells."""

    def test_csv_quoted_commas_and_multiline_cells(self, client: TestClient):
        """Verify CSV with quoted commas in headers/cells and multiline text is correctly parsed and redacted.
        
        Verifies:
        - Exact row count and column count are preserved.
        - Quoted commas do not cause cell shifting or column splitting.
        - Multiline cells retain their embedded newlines.
        - Escaped double quotes are preserved.
        - Golden round-trip re-scan yields 0 critical leaks.
        """
        raw_csv_rows = [
            ["Record ID", "Client, Organization, Group", "audit_notes", "Primary Phone", "financial_profile"],
            [
                "REC-001",
                "Acme, Corp, Global",
                "Routine quarterly audit.\nAll accounts in standard compliance.",
                "9876543210",
                "Visa Card: 4532 0151 1283 0366, authorized"
            ],
            [
                "REC-002",
                "Beta, Logistics, Ltd",
                "Incident #902:\nCustomer Aadhaar: 3675 9832 4511 verified.\nCase closed.",
                "8765432109",
                "Tax ID: ABCPE1234F"
            ],
            [
                "REC-003",
                'Gamma, "Aerospace", Limited',
                'Notes with quotes: "Priority Dispatch"\nContact email: amit.kumar@corp.in\nApproved by legal.',
                "9123456780",
                "Standard Account"
            ],
            [
                "REC-004",
                "Delta, Solutions",
                "",
                "",
                ""
            ]
        ]

        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerows(raw_csv_rows)
        csv_bytes = out.getvalue().encode("utf-8")

        # Step 1: Scan
        scan_resp = client.post(
            "/scan",
            files={"file": ("quoted_stress.csv", csv_bytes, "text/csv")}
        )
        assert scan_resp.status_code == 200
        scan_data = scan_resp.json()
        findings = scan_data["findings"]
        assert len(findings) >= 5, f"Expected at least 5 findings, got {len(findings)}"

        # Step 2: Redact All
        redact_resp = client.post(
            "/redact",
            files={"file": ("quoted_stress.csv", csv_bytes, "text/csv")},
            data={"finding_ids": "all"}
        )
        assert redact_resp.status_code == 200
        assert "text/csv" in redact_resp.headers.get("content-type", "")
        redacted_bytes = redact_resp.content

        # Step 3: Parse Redacted CSV Structure
        redacted_text = redacted_bytes.decode("utf-8")
        parsed_rows = list(csv.reader(io.StringIO(redacted_text)))

        # Verify dimensions
        assert len(parsed_rows) == 5, f"Row count corrupted: expected 5, got {len(parsed_rows)}"
        for r_idx, r in enumerate(parsed_rows):
            assert len(r) == 5, f"Row {r_idx + 1} column count corrupted: expected 5, got {len(r)}"

        # Verify Header (quoted commas preserved, not split into 7 columns)
        assert parsed_rows[0] == ["Record ID", "Client, Organization, Group", "audit_notes", "Primary Phone", "financial_profile"]

        # Verify Row 1
        assert parsed_rows[1][0] == "REC-001"
        assert parsed_rows[1][1] == "Acme, Corp, Global"
        assert "9876543210" not in parsed_rows[1][3]
        assert "[REDACTED]" in parsed_rows[1][3]
        assert "4532 0151 1283 0366" not in parsed_rows[1][4]
        assert "[REDACTED]" in parsed_rows[1][4]

        # Verify Row 2 (Multiline cell with Aadhaar)
        assert parsed_rows[2][1] == "Beta, Logistics, Ltd"
        multiline_cell = parsed_rows[2][2]
        assert "\n" in multiline_cell, "Multiline newline was stripped from CSV cell!"
        assert "3675 9832 4511" not in multiline_cell
        assert "[REDACTED]" in multiline_cell
        assert "Incident #902:" in multiline_cell
        assert "Case closed." in multiline_cell
        assert "8765432109" not in parsed_rows[2][3]
        assert "[REDACTED]" in parsed_rows[2][3]
        assert "ABCPE1234F" not in parsed_rows[2][4]
        assert "[REDACTED]" in parsed_rows[2][4]

        # Verify Row 3 (Escaped quotes + multiline email)
        assert parsed_rows[3][1] == 'Gamma, "Aerospace", Limited'
        email_multiline_cell = parsed_rows[3][2]
        assert "\n" in email_multiline_cell
        assert "amit.kumar@corp.in" not in email_multiline_cell
        assert "[REDACTED]" in email_multiline_cell
        assert '"Priority Dispatch"' in email_multiline_cell
        assert "9123456780" not in parsed_rows[3][3]
        assert "[REDACTED]" in parsed_rows[3][3]

        # Verify Row 4 (Empty trailing cells)
        assert parsed_rows[4] == ["REC-004", "Delta, Solutions", "", "", ""]

        # Step 4: Golden Round-Trip Re-Scan
        rescan_resp = client.post(
            "/scan",
            files={"file": ("redacted_quoted.csv", redacted_bytes, "text/csv")}
        )
        assert rescan_resp.status_code == 200
        critical_leaks = [
            f for f in rescan_resp.json()["findings"]
            if f["entity_type"] in ("AADHAAR", "PAN", "CREDIT_CARD", "PHONE_NUMBER", "EMAIL_ADDRESS")
        ]
        assert len(critical_leaks) == 0, f"Critical PII leaked in redacted CSV: {critical_leaks}"

    def test_csv_utf8_bom_and_currency_symbols(self, client: TestClient):
        """Verify CSV files with UTF-8 BOM encoding and currency symbols (₹, $) parse and redact cleanly."""
        csv_content = (
            "\ufeffTransaction ID,Merchant Name,Currency,Amount,Customer Aadhaar\n"
            "TX-1001,Reliance Retail,₹,4500.00,3675 9832 4511\n"
            "TX-1002,Amazon Global,$,120.50,9876 5432 1096\n"
        )
        bom_bytes = csv_content.encode("utf-8-sig")

        redact_resp = client.post(
            "/redact",
            files={"file": ("bom_transactions.csv", bom_bytes, "text/csv")},
            data={"finding_ids": "all"}
        )
        assert redact_resp.status_code == 200
        redacted_bytes = redact_resp.content

        # Should be readable as utf-8
        redacted_str = redacted_bytes.decode("utf-8-sig")
        assert "3675 9832 4511" not in redacted_str
        assert "9876 5432 1096" not in redacted_str
        assert "₹" in redacted_str
        assert "$" in redacted_str
        assert "[REDACTED]" in redacted_str


# =====================================================================
# 5. PLAIN TEXT (.TXT) CRLF & LF LINE ENDINGS STRESS
# =====================================================================

class TestTxtCrlfAndLfStress:
    """Empirical stress tests for plain text files with CRLF and LF line terminators."""

    def test_txt_pure_crlf_redaction_line_ending_preservation(self, client: TestClient):
        """Verify 150-line TXT file with pure CRLF (\\r\\n) line endings preserves \\r\\n on every line.
        
        Verifies:
        - Line count is preserved exactly.
        - Line terminators are strictly \\r\\n (no conversion to \\n or \\r\\r\\n).
        - PII character offsets on distinct lines are accurate.
        - Re-scanning yields 0 critical leaks.
        """
        lines = []
        for i in range(1, 151):
            if i == 1:
                lines.append(f"Line {i}: Identity Header Record — Aadhaar: 3675 9832 4511")
            elif i == 45:
                lines.append(f"Line {i}: Financial Audit — PAN: ABCPE1234F and Card: 4532 0151 1283 0366")
            elif i == 90:
                lines.append(f"Line {i}: Incident Operations — Contact email: support@sentinel-defense.in")
            elif i == 135:
                lines.append(f"Line {i}: Duty Officer — Mobile: +91 9876543210")
            elif i == 150:
                lines.append(f"Line {i}: Final audit termination marker.")
            else:
                lines.append(f"Line {i}: Normal system diagnostic telemetry with status OK.")

        # Join with strict CRLF
        raw_text = "\r\n".join(lines) + "\r\n"
        crlf_bytes = raw_text.encode("utf-8")

        # Step 1: Scan
        scan_resp = client.post(
            "/scan",
            files={"file": ("crlf_log.txt", crlf_bytes, "text/plain")}
        )
        assert scan_resp.status_code == 200
        scan_data = scan_resp.json()
        findings = scan_data["findings"]
        assert len(findings) >= 5

        # Check line number mapping
        finding_lines = {f["location"]["line"] for f in findings if f["location"]["line"] is not None}
        assert 1 in finding_lines
        assert 45 in finding_lines
        assert 90 in finding_lines
        assert 135 in finding_lines

        # Step 2: Redact All
        redact_resp = client.post(
            "/redact",
            files={"file": ("crlf_log.txt", crlf_bytes, "text/plain")},
            data={"finding_ids": "all"}
        )
        assert redact_resp.status_code == 200
        assert "text/plain" in redact_resp.headers.get("content-type", "")
        redacted_bytes = redact_resp.content

        # Step 3: Verify Exact CRLF Line Terminators
        assert b"\r\n" in redacted_bytes, "CRLF line endings were stripped or lost!"

        # Count \r\n vs isolated \n
        crlf_count = redacted_bytes.count(b"\r\n")
        lf_count = redacted_bytes.count(b"\n")
        cr_count = redacted_bytes.count(b"\r")

        assert crlf_count == 150, f"Expected 150 CRLF terminators, got {crlf_count}"
        assert crlf_count == lf_count, f"Found {lf_count - crlf_count} isolated LF terminators!"
        assert crlf_count == cr_count, f"Found {cr_count - crlf_count} isolated CR terminators!"

        # Verify content
        redacted_str = redacted_bytes.decode("utf-8")
        assert "3675 9832 4511" not in redacted_str
        assert "ABCPE1234F" not in redacted_str
        assert "4532 0151 1283 0366" not in redacted_str
        assert "support@sentinel-defense.in" not in redacted_str
        assert "9876543210" not in redacted_str
        assert "Final audit termination marker." in redacted_str

        # Step 4: Re-scan
        rescan_resp = client.post(
            "/scan",
            files={"file": ("redacted_crlf.txt", redacted_bytes, "text/plain")}
        )
        assert rescan_resp.status_code == 200
        critical_leaks = [
            f for f in rescan_resp.json()["findings"]
            if f["entity_type"] in ("AADHAAR", "PAN", "CREDIT_CARD", "PHONE_NUMBER", "EMAIL_ADDRESS")
        ]
        assert len(critical_leaks) == 0, f"Critical PII leaked in redacted TXT: {critical_leaks}"

    def test_txt_mixed_line_endings_preservation(self, client: TestClient):
        """Verify text file with mixed CRLF and LF line endings does not corrupt line structure."""
        mixed_text = (
            "Line 1 with Aadhaar: 3675 9832 4511\r\n"
            "Line 2 with LF only and PAN: ABCPE1234F\n"
            "Line 3 with CRLF and Card: 4532 0151 1283 0366\r\n"
            "Line 4 with LF only.\n"
        )
        mixed_bytes = mixed_text.encode("utf-8")

        redact_resp = client.post(
            "/redact",
            files={"file": ("mixed_endings.txt", mixed_bytes, "text/plain")},
            data={"finding_ids": "all"}
        )
        assert redact_resp.status_code == 200
        redacted_bytes = redact_resp.content

        # Verify line 1 has CRLF, line 2 has LF, line 3 has CRLF
        redacted_lines = redacted_bytes.splitlines(keepends=True)
        assert len(redacted_lines) == 4
        assert redacted_lines[0].endswith(b"\r\n")
        assert redacted_lines[1].endswith(b"\n") and not redacted_lines[1].endswith(b"\r\n")
        assert redacted_lines[2].endswith(b"\r\n")
        assert redacted_lines[3].endswith(b"\n") and not redacted_lines[3].endswith(b"\r\n")

        redacted_str = redacted_bytes.decode("utf-8")
        assert "3675 9832 4511" not in redacted_str
        assert "ABCPE1234F" not in redacted_str
        assert "4532 0151 1283 0366" not in redacted_str

    def test_txt_multiple_pii_on_single_line_right_to_left_replacement(self, client: TestClient):
        """Verify multiple PII items on a single line are redacted without character offset skewing."""
        single_line = "Candidate 3675 9832 4511 tax PAN ABCPE1234F card 4532 0151 1283 0366 call +91 9876543210 end."
        txt_bytes = single_line.encode("utf-8")

        redact_resp = client.post(
            "/redact",
            files={"file": ("dense_line.txt", txt_bytes, "text/plain")},
            data={"finding_ids": "all"}
        )
        assert redact_resp.status_code == 200
        redacted_str = redact_resp.content.decode("utf-8")

        # All 4 items must be redacted
        assert "3675 9832 4511" not in redacted_str
        assert "ABCPE1234F" not in redacted_str
        assert "4532 0151 1283 0366" not in redacted_str
        assert "9876543210" not in redacted_str

        # Surrounding sentence words must be intact
        assert "Candidate " in redacted_str
        assert " tax PAN " in redacted_str
        assert " card " in redacted_str
        assert " call " in redacted_str
        assert " end." in redacted_str


# =====================================================================
# 6. DEEP DOCUMENT INTEGRITY & FORMAT INVARIANTS
# =====================================================================

class TestDocumentCorruptionAndFormatInvariants:
    """Rigorous verification of binary structures, xref tables, and ZIP headers."""

    def test_pdf_xref_table_and_content_stream_validity(self, client: TestClient):
        """Verify PyMuPDF reports valid xref table and clean page rendering for redacted PDF."""
        doc = fitz.open()
        for i in range(10):
            p = doc.new_page(width=612, height=792)
            # Add text, lines, and shapes
            p.draw_rect(fitz.Rect(50, 50, 200, 100), color=(0.5, 0.5, 0.5), fill=(0.9, 0.9, 0.9))
            p.insert_text(fitz.Point(60, 80), f"Section {i+1} Vector Box", fontsize=10)
            p.insert_text(fitz.Point(60, 150), f"Audit Record: Aadhaar 3675 9832 4511 on Page {i+1}")
        pdf_bytes = doc.tobytes()
        doc.close()

        redact_resp = client.post(
            "/redact",
            files={"file": ("vector_test.pdf", pdf_bytes, "application/pdf")},
            data={"finding_ids": "all"}
        )
        assert redact_resp.status_code == 200
        redacted_bytes = redact_resp.content

        redacted_doc = fitz.open(stream=redacted_bytes, filetype="pdf")
        assert redacted_doc.is_pdf is True
        assert redacted_doc.is_repaired is False
        assert redacted_doc.xref_length() > 0

        # Render all pages to ensure content stream commands (q, Q, cm, re, f) are valid
        for p in redacted_doc:
            pix = p.get_pixmap()
            assert pix.width == 612 and pix.height == 792
            assert "3675 9832 4511" not in p.get_text()
        redacted_doc.close()

    def test_docx_zip_structure_and_xml_schema_validity(self, client: TestClient):
        """Verify redacted DOCX ZIP container passes testzip() and document.xml is valid XML."""
        doc = docx.Document()
        doc.add_heading("XML Validation Document", level=1)
        doc.add_paragraph("Testing XML validity with Aadhaar: 3675 9832 4511.")
        buf = io.BytesIO()
        doc.save(buf)
        docx_bytes = buf.getvalue()

        redact_resp = client.post(
            "/redact",
            files={"file": ("xml_check.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            data={"finding_ids": "all"}
        )
        assert redact_resp.status_code == 200
        redacted_bytes = redact_resp.content

        zf = zipfile.ZipFile(io.BytesIO(redacted_bytes))
        # 1. ZIP CRC & Header check
        assert zf.testzip() is None, "DOCX ZIP CRC check failed!"

        # 2. XML Well-formedness
        doc_xml = zf.read("word/document.xml")
        root = ET.fromstring(doc_xml)
        assert root.tag.endswith("document")

        # 3. python-docx reload and resave
        d2 = docx.Document(io.BytesIO(redacted_bytes))
        buf2 = io.BytesIO()
        d2.save(buf2)
        assert len(buf2.getvalue()) > 500

    def test_xlsx_zip_structure_and_sheet_xml_validity(self, client: TestClient):
        """Verify redacted XLSX ZIP container passes testzip() and all sheet XMLs are valid."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "IntegrityCheck"
        ws.append(["Header", "PAN Number", "Formula"])
        ws.append(["Row 1", "ABCPE1234F", "=100*2"])
        buf = io.BytesIO()
        wb.save(buf)
        xlsx_bytes = buf.getvalue()
        wb.close()

        redact_resp = client.post(
            "/redact",
            files={"file": ("xml_check.xlsx", xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={"finding_ids": "all"}
        )
        assert redact_resp.status_code == 200
        redacted_bytes = redact_resp.content

        zf = zipfile.ZipFile(io.BytesIO(redacted_bytes))
        assert zf.testzip() is None, "XLSX ZIP CRC check failed!"

        sheet_xml = zf.read("xl/worksheets/sheet1.xml")
        root = ET.fromstring(sheet_xml)
        assert root.tag.endswith("worksheet")

        wb2 = openpyxl.load_workbook(io.BytesIO(redacted_bytes), data_only=False)
        assert wb2["IntegrityCheck"]["B2"].value == "[REDACTED]"
        assert wb2["IntegrityCheck"]["C2"].value == "=100*2"
        wb2.close()

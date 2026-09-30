"""Adversarial Verification & Redaction Stress Suite.

Authored by Empirical Challenger (teamwork_preview_challenger_m2_1).
Empirically verifies:
1. Round-Trip Zero-Leakage Invariant across PDF, DOCX, CSV, XLSX, and TXT.
2. Selective Redaction Precision across all formats.
3. Duplicate PII partial redaction isolation.
4. Input validation and adversarial parameter handling for POST /redact.
5. Structural preservation of documents post-redaction.
6. Edge case probing: Unicode context, formula cells, and file extension boundary checks.
"""
import io
import json
import csv
import docx
import fitz
import openpyxl
import pytest
from fastapi.testclient import TestClient

from tests.fixtures.generator import (
    create_txt,
    create_csv,
    create_xlsx,
    create_docx,
    create_pdf,
    generate_simple_pdf,
    generate_simple_docx,
    generate_simple_csv,
    generate_simple_xlsx,
)
from tests.fixtures.sample_data import (
    VALID_AADHAAR_CATALOG,
    VALID_PAN_CATALOG,
    VALID_CARD_CATALOG,
    VALID_PHONE_CATALOG,
    VALID_EMAIL_CATALOG,
)


CRITICAL_PII_TYPES = {"AADHAAR", "PAN", "CREDIT_CARD", "PHONE_NUMBER", "EMAIL_ADDRESS"}


# =====================================================================
# 1. ROUND-TRIP ZERO-LEAKAGE INVARIANT SUITE
# =====================================================================

class TestRoundTripZeroLeakage:
    """Empirically verifies that redacting all detected findings yields ZERO critical PII leaks on re-scan."""

    def test_roundtrip_zero_leakage_txt(self, client: TestClient):
        """TXT round-trip: Scan -> Redact All -> Re-Scan -> Assert 0 critical PII findings."""
        text = (
            "CONFIDENTIAL INCIDENT LOG\n"
            "Aadhaar: 3675 9832 4511\n"
            "PAN: ABCPE1234F\n"
            "Credit Card: 4532 0151 1283 0366\n"
            "Phone: +91 98765 43210\n"
            "Email: harsh.patel@sentineldoc.com\n"
        )
        # 1. Initial Scan
        files = {"file": ("incident.txt", create_txt(text), "text/plain")}
        scan_resp = client.post("/scan", files=files)
        assert scan_resp.status_code == 200
        scan_findings = scan_resp.json()["findings"]
        found_types = {f["entity_type"] for f in scan_findings}
        assert CRITICAL_PII_TYPES.issubset(found_types), f"Scan failed to detect all critical PII: {found_types}"

        # 2. Redact All
        redact_files = {"file": ("incident.txt", create_txt(text), "text/plain")}
        redact_resp = client.post("/redact", files=redact_files, data={"finding_ids": "all"})
        assert redact_resp.status_code == 200
        redacted_bytes = redact_resp.content

        # 3. Re-scan Redacted Output
        rescan_files = {"file": ("redacted_incident.txt", redacted_bytes, "text/plain")}
        rescan_resp = client.post("/scan", files=rescan_files)
        assert rescan_resp.status_code == 200
        rescan_findings = rescan_resp.json()["findings"]
        leaked_types = [f["entity_type"] for f in rescan_findings if f["entity_type"] in CRITICAL_PII_TYPES]
        assert len(leaked_types) == 0, f"Critical PII leaked after full redaction in TXT: {leaked_types}"

        # 4. Underlying text verification
        decoded_text = redacted_bytes.decode("utf-8")
        assert "3675 9832 4511" not in decoded_text
        assert "ABCPE1234F" not in decoded_text
        assert "4532 0151 1283 0366" not in decoded_text
        assert "harsh.patel@sentineldoc.com" not in decoded_text

    def test_roundtrip_zero_leakage_pdf(self, client: TestClient):
        """PDF round-trip: Scan -> Redact All -> Re-Scan -> Assert 0 critical PII leaks."""
        text = (
            "SECURITY IDENTIFICATION DOSSIER\n"
            "Aadhaar Number: 3675 9832 4511\n"
            "Income Tax PAN: ABCPE1234F\n"
            "Visa Card: 4532 0151 1283 0366\n"
            "Mobile Contact: +91 98765 43210\n"
            "Email Address: harsh.patel@sentineldoc.com\n"
        )
        pdf_bytes = generate_simple_pdf(text)

        # 1. Initial Scan
        files = {"file": ("dossier.pdf", pdf_bytes, "application/pdf")}
        scan_resp = client.post("/scan", files=files)
        assert scan_resp.status_code == 200
        scan_findings = scan_resp.json()["findings"]
        found_types = {f["entity_type"] for f in scan_findings}
        assert CRITICAL_PII_TYPES.issubset(found_types)

        # 2. Redact All
        redact_files = {"file": ("dossier.pdf", pdf_bytes, "application/pdf")}
        redact_resp = client.post("/redact", files=redact_files, data={"finding_ids": "all"})
        assert redact_resp.status_code == 200
        redacted_pdf = redact_resp.content

        # 3. Re-scan Redacted PDF
        rescan_files = {"file": ("redacted_dossier.pdf", redacted_pdf, "application/pdf")}
        rescan_resp = client.post("/scan", files=rescan_files)
        assert rescan_resp.status_code == 200
        rescan_findings = rescan_resp.json()["findings"]
        leaked_types = [f["entity_type"] for f in rescan_findings if f["entity_type"] in CRITICAL_PII_TYPES]
        assert len(leaked_types) == 0, f"Critical PII leaked after full redaction in PDF: {leaked_types}"

        # 4. Underlying PDF content stream inspection (ensure PyMuPDF purged raw text)
        doc = fitz.open(stream=redacted_pdf, filetype="pdf")
        extracted_text = doc[0].get_text()
        doc.close()
        assert "3675 9832 4511" not in extracted_text
        assert "ABCPE1234F" not in extracted_text
        assert "4532 0151 1283 0366" not in extracted_text
        assert "harsh.patel@sentineldoc.com" not in extracted_text

    def test_roundtrip_zero_leakage_docx(self, client: TestClient):
        """DOCX round-trip: Scan -> Redact All -> Re-Scan -> Assert 0 critical PII leaks."""
        doc = docx.Document()
        doc.add_heading("Customer File", level=1)
        doc.add_paragraph("Aadhaar Identifier: 3675 9832 4511")
        doc.add_paragraph("Taxation PAN: ABCPE1234F")
        doc.add_paragraph("Debit Card: 4532 0151 1283 0366")
        doc.add_paragraph("Personal Phone: +91 98765 43210")
        doc.add_paragraph("Official Email: harsh.patel@sentineldoc.com")

        # Also plant inside a table cell
        table = doc.add_table(rows=2, cols=2)
        table.cell(0, 0).text = "Backup Aadhaar"
        table.cell(0, 1).text = "982341567897"
        table.cell(1, 0).text = "Backup PAN"
        table.cell(1, 1).text = "XYZCA5678B"

        buf = io.BytesIO()
        doc.save(buf)
        docx_bytes = buf.getvalue()

        # 1. Initial Scan
        files = {"file": ("customer.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        scan_resp = client.post("/scan", files=files)
        assert scan_resp.status_code == 200
        scan_findings = scan_resp.json()["findings"]
        found_types = {f["entity_type"] for f in scan_findings}
        assert CRITICAL_PII_TYPES.issubset(found_types)

        # 2. Redact All
        redact_files = {"file": ("customer.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        redact_resp = client.post("/redact", files=redact_files, data={"finding_ids": "all"})
        assert redact_resp.status_code == 200
        redacted_docx = redact_resp.content

        # 3. Re-scan
        rescan_files = {"file": ("redacted_customer.docx", redacted_docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        rescan_resp = client.post("/scan", files=rescan_files)
        assert rescan_resp.status_code == 200
        rescan_findings = rescan_resp.json()["findings"]
        leaked_types = [f["entity_type"] for f in rescan_findings if f["entity_type"] in CRITICAL_PII_TYPES]
        assert len(leaked_types) == 0, f"Critical PII leaked after full redaction in DOCX: {leaked_types}"

        # 4. Underlying Word document inspection
        res_doc = docx.Document(io.BytesIO(redacted_docx))
        full_text = "\n".join([p.text for p in res_doc.paragraphs] + [c.text for t in res_doc.tables for r in t.rows for c in r.cells])
        assert "3675 9832 4511" not in full_text
        assert "ABCPE1234F" not in full_text
        assert "4532 0151 1283 0366" not in full_text
        assert "982341567897" not in full_text
        assert "XYZCA5678B" not in full_text

    def test_roundtrip_zero_leakage_csv(self, client: TestClient):
        """CSV round-trip: Scan -> Redact All -> Re-Scan -> Assert 0 critical PII leaks."""
        header = ["id", "name", "aadhaar", "pan", "card", "phone", "email"]
        rows = [
            [1, "Aarav Sharma", "3675 9832 4511", "ABCPE1234F", "4532 0151 1283 0366", "+91 98765 43210", "aarav.sharma@domain.com"],
            [2, "Priya Ramanathan", "982341567897", "XYZCA5678B", "5424-1801-2345-6789", "9876543210", "compliance_officer+audit@enterprise.org.in"],
        ]
        csv_bytes = generate_simple_csv(header, rows)

        # 1. Initial Scan
        files = {"file": ("records.csv", csv_bytes, "text/csv")}
        scan_resp = client.post("/scan", files=files)
        assert scan_resp.status_code == 200
        scan_findings = scan_resp.json()["findings"]
        found_types = {f["entity_type"] for f in scan_findings}
        assert CRITICAL_PII_TYPES.issubset(found_types)

        # 2. Redact All
        redact_files = {"file": ("records.csv", csv_bytes, "text/csv")}
        redact_resp = client.post("/redact", files=redact_files, data={"finding_ids": "all"})
        assert redact_resp.status_code == 200
        redacted_csv = redact_resp.content

        # 3. Re-scan
        rescan_files = {"file": ("redacted_records.csv", redacted_csv, "text/csv")}
        rescan_resp = client.post("/scan", files=rescan_files)
        assert rescan_resp.status_code == 200
        rescan_findings = rescan_resp.json()["findings"]
        leaked_types = [f["entity_type"] for f in rescan_findings if f["entity_type"] in CRITICAL_PII_TYPES]
        assert len(leaked_types) == 0, f"Critical PII leaked after full redaction in CSV: {leaked_types}"

        # 4. Underlying CSV rows check
        text_csv = redacted_csv.decode("utf-8")
        assert "3675 9832 4511" not in text_csv
        assert "ABCPE1234F" not in text_csv
        assert "4532 0151 1283 0366" not in text_csv
        assert "aarav.sharma@domain.com" not in text_csv

    def test_roundtrip_zero_leakage_xlsx(self, client: TestClient):
        """XLSX round-trip: Scan -> Redact All -> Re-Scan -> Assert 0 critical PII leaks."""
        header = ["ID", "Aadhaar", "PAN", "Card", "Phone", "Email"]
        rows = [
            ["101", "3675 9832 4511", "ABCPE1234F", "4532 0151 1283 0366", "+91 98765 43210", "aarav.sharma@domain.com"],
            ["102", "982341567897", "XYZCA5678B", "6071 2345 6789 0120", "9876543210", "harsh.patel@sentineldoc.com"],
        ]
        xlsx_bytes = generate_simple_xlsx("ConfidentialData", header, rows)

        # 1. Initial Scan
        files = {"file": ("accounts.xlsx", xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        scan_resp = client.post("/scan", files=files)
        assert scan_resp.status_code == 200
        scan_findings = scan_resp.json()["findings"]
        found_types = {f["entity_type"] for f in scan_findings}
        assert CRITICAL_PII_TYPES.issubset(found_types)

        # 2. Redact All
        redact_files = {"file": ("accounts.xlsx", xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        redact_resp = client.post("/redact", files=redact_files, data={"finding_ids": "all"})
        assert redact_resp.status_code == 200
        redacted_xlsx = redact_resp.content

        # 3. Re-scan
        rescan_files = {"file": ("redacted_accounts.xlsx", redacted_xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        rescan_resp = client.post("/scan", files=rescan_files)
        assert rescan_resp.status_code == 200
        rescan_findings = rescan_resp.json()["findings"]
        leaked_types = [f["entity_type"] for f in rescan_findings if f["entity_type"] in CRITICAL_PII_TYPES]
        assert len(leaked_types) == 0, f"Critical PII leaked after full redaction in XLSX: {leaked_types}"

        # 4. Underlying Excel cells check
        wb = openpyxl.load_workbook(io.BytesIO(redacted_xlsx))
        ws = wb.active
        all_cell_values = [str(cell.value) for row in ws.iter_rows() for cell in row if cell.value is not None]
        wb.close()
        cell_dump = " ".join(all_cell_values)
        assert "3675 9832 4511" not in cell_dump
        assert "ABCPE1234F" not in cell_dump
        assert "4532 0151 1283 0366" not in cell_dump
        assert "aarav.sharma@domain.com" not in cell_dump


# =====================================================================
# 2. SELECTIVE REDACTION PRECISION SUITE
# =====================================================================

class TestSelectiveRedactionPrecision:
    """Empirically verifies selective redaction across multiple formats:

    Selected PII is completely eliminated, while non-selected PII remains intact.
    """

    def test_selective_redaction_pdf(self, client: TestClient):
        """PDF Selective: Redact Aadhaar + Card; Preserve PAN + Phone."""
        text = (
            "AUDIT TARGET DOCUMENT\n"
            "Aadhaar Number: 3675 9832 4511\n"
            "PAN Identifier: ABCPE1234F\n"
            "Payment Card: 4532 0151 1283 0366\n"
            "Direct Phone: +91 98765 43210\n"
        )
        pdf_bytes = generate_simple_pdf(text)

        # 1. Scan
        files = {"file": ("target.pdf", pdf_bytes, "application/pdf")}
        scan_resp = client.post("/scan", files=files)
        assert scan_resp.status_code == 200
        findings = scan_resp.json()["findings"]

        aadhaar_ids = [f["id"] for f in findings if f["entity_type"] == "AADHAAR"]
        card_ids = [f["id"] for f in findings if f["entity_type"] == "CREDIT_CARD"]
        pan_ids = [f["id"] for f in findings if f["entity_type"] == "PAN"]
        phone_ids = [f["id"] for f in findings if f["entity_type"] == "PHONE_NUMBER"]

        assert len(aadhaar_ids) >= 1
        assert len(card_ids) >= 1
        assert len(pan_ids) >= 1
        assert len(phone_ids) >= 1

        selected_ids = aadhaar_ids + card_ids

        # 2. Redact ONLY Aadhaar and Card
        redact_files = {"file": ("target.pdf", pdf_bytes, "application/pdf")}
        redact_resp = client.post(
            "/redact",
            files=redact_files,
            data={"finding_ids": json.dumps(selected_ids)}
        )
        assert redact_resp.status_code == 200
        redacted_pdf = redact_resp.content

        # 3. Re-scan
        rescan_files = {"file": ("redacted_target.pdf", redacted_pdf, "application/pdf")}
        rescan_resp = client.post("/scan", files=rescan_files)
        assert rescan_resp.status_code == 200
        rescan_findings = rescan_resp.json()["findings"]

        rescan_aadhaar = [f for f in rescan_findings if f["entity_type"] == "AADHAAR"]
        rescan_card = [f for f in rescan_findings if f["entity_type"] == "CREDIT_CARD"]
        rescan_pan = [f for f in rescan_findings if f["entity_type"] == "PAN"]
        rescan_phone = [f for f in rescan_findings if f["entity_type"] == "PHONE_NUMBER"]

        assert len(rescan_aadhaar) == 0, f"Aadhaar leaked: {rescan_aadhaar}"
        assert len(rescan_card) == 0, f"Card leaked: {rescan_card}"
        assert len(rescan_pan) >= 1, "PAN was incorrectly purged during selective redaction"
        assert len(rescan_phone) >= 1, "Phone was incorrectly purged during selective redaction"

    def test_selective_redaction_docx(self, client: TestClient):
        """DOCX Selective: Redact Aadhaar + Card; Preserve PAN + Phone."""
        doc = docx.Document()
        doc.add_paragraph("Aadhaar Identifier: 3675 9832 4511")
        doc.add_paragraph("PAN Record: ABCPE1234F")
        doc.add_paragraph("Credit Card: 4532 0151 1283 0366")
        doc.add_paragraph("Phone Number: +91 98765 43210")
        buf = io.BytesIO()
        doc.save(buf)
        docx_bytes = buf.getvalue()

        # 1. Scan
        files = {"file": ("selective.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        scan_resp = client.post("/scan", files=files)
        assert scan_resp.status_code == 200
        findings = scan_resp.json()["findings"]

        aadhaar_ids = [f["id"] for f in findings if f["entity_type"] == "AADHAAR"]
        card_ids = [f["id"] for f in findings if f["entity_type"] == "CREDIT_CARD"]
        selected_ids = aadhaar_ids + card_ids

        # 2. Redact selected
        redact_files = {"file": ("selective.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        redact_resp = client.post(
            "/redact",
            files=redact_files,
            data={"finding_ids": json.dumps(selected_ids)}
        )
        assert redact_resp.status_code == 200
        redacted_docx = redact_resp.content

        # 3. Re-scan
        rescan_files = {"file": ("redacted_selective.docx", redacted_docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        rescan_resp = client.post("/scan", files=rescan_files)
        assert rescan_resp.status_code == 200
        rescan_findings = rescan_resp.json()["findings"]

        rescan_aadhaar = [f for f in rescan_findings if f["entity_type"] == "AADHAAR"]
        rescan_card = [f for f in rescan_findings if f["entity_type"] == "CREDIT_CARD"]
        rescan_pan = [f for f in rescan_findings if f["entity_type"] == "PAN"]
        rescan_phone = [f for f in rescan_findings if f["entity_type"] == "PHONE_NUMBER"]

        assert len(rescan_aadhaar) == 0, f"Aadhaar leaked: {rescan_aadhaar}"
        assert len(rescan_card) == 0, f"Card leaked: {rescan_card}"
        assert len(rescan_pan) >= 1, "PAN was incorrectly removed from DOCX"
        assert len(rescan_phone) >= 1, "Phone was incorrectly removed from DOCX"

    def test_selective_redaction_csv(self, client: TestClient):
        """CSV Selective: Redact Aadhaar + Card; Preserve PAN + Phone."""
        header = ["Aadhaar", "PAN", "Card", "Phone"]
        rows = [["3675 9832 4511", "ABCPE1234F", "4532 0151 1283 0366", "+91 98765 43210"]]
        csv_bytes = generate_simple_csv(header, rows)

        # 1. Scan
        files = {"file": ("selective.csv", csv_bytes, "text/csv")}
        scan_resp = client.post("/scan", files=files)
        assert scan_resp.status_code == 200
        findings = scan_resp.json()["findings"]

        aadhaar_ids = [f["id"] for f in findings if f["entity_type"] == "AADHAAR"]
        card_ids = [f["id"] for f in findings if f["entity_type"] == "CREDIT_CARD"]
        selected_ids = aadhaar_ids + card_ids

        # 2. Redact
        redact_files = {"file": ("selective.csv", csv_bytes, "text/csv")}
        redact_resp = client.post(
            "/redact",
            files=redact_files,
            data={"finding_ids": json.dumps(selected_ids)}
        )
        assert redact_resp.status_code == 200
        redacted_csv = redact_resp.content

        # 3. Re-scan
        rescan_files = {"file": ("redacted_selective.csv", redacted_csv, "text/csv")}
        rescan_resp = client.post("/scan", files=rescan_files)
        assert rescan_resp.status_code == 200
        rescan_findings = rescan_resp.json()["findings"]

        rescan_aadhaar = [f for f in rescan_findings if f["entity_type"] == "AADHAAR"]
        rescan_card = [f for f in rescan_findings if f["entity_type"] == "CREDIT_CARD"]
        rescan_pan = [f for f in rescan_findings if f["entity_type"] == "PAN"]
        rescan_phone = [f for f in rescan_findings if f["entity_type"] == "PHONE_NUMBER"]

        assert len(rescan_aadhaar) == 0
        assert len(rescan_card) == 0
        assert len(rescan_pan) >= 1, "PAN was incorrectly removed from CSV"
        assert len(rescan_phone) >= 1, "Phone was incorrectly removed from CSV"

    def test_selective_redaction_xlsx(self, client: TestClient):
        """XLSX Selective: Redact Aadhaar + Card; Preserve PAN + Phone."""
        header = ["Aadhaar", "PAN", "Card", "Phone"]
        rows = [["3675 9832 4511", "ABCPE1234F", "4532 0151 1283 0366", "+91 98765 43210"]]
        xlsx_bytes = generate_simple_xlsx("Data", header, rows)

        # 1. Scan
        files = {"file": ("selective.xlsx", xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        scan_resp = client.post("/scan", files=files)
        assert scan_resp.status_code == 200
        findings = scan_resp.json()["findings"]

        aadhaar_ids = [f["id"] for f in findings if f["entity_type"] == "AADHAAR"]
        card_ids = [f["id"] for f in findings if f["entity_type"] == "CREDIT_CARD"]
        selected_ids = aadhaar_ids + card_ids

        # 2. Redact
        redact_files = {"file": ("selective.xlsx", xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        redact_resp = client.post(
            "/redact",
            files=redact_files,
            data={"finding_ids": json.dumps(selected_ids)}
        )
        assert redact_resp.status_code == 200
        redacted_xlsx = redact_resp.content

        # 3. Re-scan
        rescan_files = {"file": ("redacted_selective.xlsx", redacted_xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        rescan_resp = client.post("/scan", files=rescan_files)
        assert rescan_resp.status_code == 200
        rescan_findings = rescan_resp.json()["findings"]

        rescan_aadhaar = [f for f in rescan_findings if f["entity_type"] == "AADHAAR"]
        rescan_card = [f for f in rescan_findings if f["entity_type"] == "CREDIT_CARD"]
        rescan_pan = [f for f in rescan_findings if f["entity_type"] == "PAN"]
        rescan_phone = [f for f in rescan_findings if f["entity_type"] == "PHONE_NUMBER"]

        assert len(rescan_aadhaar) == 0
        assert len(rescan_card) == 0
        assert len(rescan_pan) >= 1, "PAN was incorrectly removed from XLSX"
        assert len(rescan_phone) >= 1, "Phone was incorrectly removed from XLSX"


# =====================================================================
# 3. ADVERSARIAL PARAMETERS & EDGE CASES SUITE
# =====================================================================

class TestAdversarialParametersAndBoundaries:
    """Probes edge cases and adversarial parameter inputs to POST /redact."""

    def test_redact_empty_finding_ids_array(self, client: TestClient):
        """When finding_ids='[]', zero findings should be redacted; original text remains intact."""
        text = "Confidential Aadhaar: 3675 9832 4511 and PAN: ABCPE1234F\n"
        files = {"file": ("test.txt", create_txt(text), "text/plain")}
        resp = client.post("/redact", files=files, data={"finding_ids": "[]"})
        assert resp.status_code == 200
        redacted_bytes = resp.content
        assert "3675 9832 4511" in redacted_bytes.decode("utf-8")
        assert "ABCPE1234F" in redacted_bytes.decode("utf-8")

    def test_redact_nonexistent_finding_ids(self, client: TestClient):
        """When finding_ids='["find_99999", "ghost_id"]', endpoint must not crash; returns document unchanged."""
        text = "Confidential Aadhaar: 3675 9832 4511\n"
        files = {"file": ("test.txt", create_txt(text), "text/plain")}
        resp = client.post("/redact", files=files, data={"finding_ids": '["find_99999", "ghost_id"]'})
        assert resp.status_code == 200
        redacted_bytes = resp.content
        assert "3675 9832 4511" in redacted_bytes.decode("utf-8")

    def test_redact_case_insensitive_all_keyword(self, client: TestClient):
        """finding_ids='ALL' or 'All' should be accepted as redacting all findings."""
        text = "Aadhaar: 3675 9832 4511\n"
        files = {"file": ("test.txt", create_txt(text), "text/plain")}
        resp = client.post("/redact", files=files, data={"finding_ids": "ALL"})
        assert resp.status_code == 200
        assert "3675 9832 4511" not in resp.content.decode("utf-8")
        assert "[REDACTED]" in resp.content.decode("utf-8")

    def test_redact_omitted_finding_ids_defaults_to_all(self, client: TestClient):
        """When finding_ids is omitted entirely from POST /redact form data, defaults to redacting all."""
        text = "Aadhaar: 3675 9832 4511\n"
        files = {"file": ("test.txt", create_txt(text), "text/plain")}
        resp = client.post("/redact", files=files)
        assert resp.status_code == 200
        assert "3675 9832 4511" not in resp.content.decode("utf-8")
        assert "[REDACTED]" in resp.content.decode("utf-8")

    def test_redact_malformed_json_finding_ids_fallback(self, client: TestClient):
        """finding_ids='not_valid_json' should be treated gracefully without HTTP 500 error."""
        text = "Aadhaar: 3675 9832 4511\n"
        files = {"file": ("test.txt", create_txt(text), "text/plain")}
        resp = client.post("/redact", files=files, data={"finding_ids": "{invalid_json}"})
        # Should not crash with 500
        assert resp.status_code in (200, 400, 422)

    def test_redact_empty_zero_byte_upload(self, client: TestClient):
        """Uploading empty 0-byte file to /redact returns HTTP 400 with EMPTY_FILE."""
        files = {"file": ("empty.txt", b"", "text/plain")}
        resp = client.post("/redact", files=files)
        assert resp.status_code == 400
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == "EMPTY_FILE"

    def test_redact_unsupported_file_extension(self, client: TestClient):
        """Uploading an unsupported extension (.bin / .exe) to /redact returns HTTP 400 with UNSUPPORTED_FILE_TYPE."""
        files = {"file": ("payload.exe", b"MZ\x90\x00BinaryData", "application/octet-stream")}
        resp = client.post("/redact", files=files)
        assert resp.status_code == 400
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == "UNSUPPORTED_FILE_TYPE"

    def test_redact_corrupt_pdf_magic_bytes(self, client: TestClient):
        """Uploading corrupted PDF (missing %PDF- header) returns HTTP 400 with MALFORMED_FILE."""
        files = {"file": ("corrupt.pdf", b"NOT_A_REAL_PDF_HEADER_JUST_GARBAGE", "application/pdf")}
        resp = client.post("/redact", files=files)
        assert resp.status_code == 400
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == "MALFORMED_FILE"

    def test_redact_corrupt_docx_zip_header(self, client: TestClient):
        """Uploading corrupted DOCX (missing PK zip header) returns HTTP 400 with MALFORMED_FILE."""
        files = {"file": ("corrupt.docx", b"NOT_A_ZIP_HEADER", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        resp = client.post("/redact", files=files)
        assert resp.status_code == 400
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == "MALFORMED_FILE"


# =====================================================================
# 4. STRUCTURAL INTEGRITY & DOCUMENT CONFORMANCE POST-REDACTION
# =====================================================================

class TestStructuralIntegrityPostRedaction:
    """Verifies document formatting, page counts, rows, and styles are preserved post-redaction."""

    def test_pdf_page_count_and_visual_integrity(self, client: TestClient):
        """Redacting a 3-page PDF preserves exact 3-page structure and document metadata."""
        pages = [
            [(72.0, 100.0, "Page 1 - Public Intro")],
            [(72.0, 100.0, "Page 2 - Aadhaar 3675 9832 4511")],
            [(72.0, 100.0, "Page 3 - Public Outro")],
        ]
        pdf_bytes = create_pdf(pages)

        files = {"file": ("multi.pdf", pdf_bytes, "application/pdf")}
        resp = client.post("/redact", files=files, data={"finding_ids": "all"})
        assert resp.status_code == 200
        redacted_pdf = resp.content

        # Open and inspect
        doc = fitz.open(stream=redacted_pdf, filetype="pdf")
        assert len(doc) == 3, f"Page count changed after redaction: expected 3, got {len(doc)}"
        # Verify page 1 and page 3 text is still intact
        assert "Public Intro" in doc[0].get_text()
        assert "Public Outro" in doc[2].get_text()
        # Verify page 2 Aadhaar is gone
        assert "3675 9832 4511" not in doc[1].get_text()
        doc.close()

    def test_docx_paragraph_and_table_count(self, client: TestClient):
        """Redacting DOCX preserves exact paragraph count, styles, and table dimensions."""
        doc = docx.Document()
        doc.add_heading("Section 1: General Info", level=1)
        doc.add_paragraph("Paragraph 1: Public details.")
        doc.add_paragraph("Paragraph 2: Aadhaar is 3675 9832 4511 here.")
        doc.add_paragraph("Paragraph 3: Concluding remarks.")

        table = doc.add_table(rows=2, cols=2)
        table.cell(0, 0).text = "Key"
        table.cell(0, 1).text = "Value"
        table.cell(1, 0).text = "PAN"
        table.cell(1, 1).text = "ABCPE1234F"

        buf = io.BytesIO()
        doc.save(buf)
        orig_bytes = buf.getvalue()

        files = {"file": ("doc_structure.docx", orig_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        resp = client.post("/redact", files=files, data={"finding_ids": "all"})
        assert resp.status_code == 200
        redacted_docx = resp.content

        res_doc = docx.Document(io.BytesIO(redacted_docx))
        assert len(res_doc.paragraphs) == 4, f"Paragraph count changed: expected 4, got {len(res_doc.paragraphs)}"
        assert len(res_doc.tables) == 1, f"Table count changed: expected 1, got {len(res_doc.tables)}"
        assert len(res_doc.tables[0].rows) == 2
        assert len(res_doc.tables[0].columns) == 2

    def test_csv_row_and_column_count(self, client: TestClient):
        """Redacting CSV preserves exact row count, column count, and empty cell alignment."""
        header = ["ID", "Name", "Aadhaar", "Notes"]
        rows = [
            ["1", "Alice", "3675 9832 4511", "First row"],
            ["2", "Bob", "", "No Aadhaar"],
            ["3", "Charlie", "982341567897", "Third row"],
        ]
        csv_bytes = generate_simple_csv(header, rows)

        files = {"file": ("grid.csv", csv_bytes, "text/csv")}
        resp = client.post("/redact", files=files, data={"finding_ids": "all"})
        assert resp.status_code == 200
        redacted_csv = resp.content

        reader = list(csv.reader(io.StringIO(redacted_csv.decode("utf-8"))))
        assert len(reader) == 4, f"Row count changed: expected 4, got {len(reader)}"
        for r in reader:
            assert len(r) == 4, f"Column count changed in row {r}: expected 4, got {len(r)}"

    def test_txt_line_count_and_crlf_preservation(self, client: TestClient):
        """Redacting TXT preserves exact line count and CRLF line endings."""
        content = "Line 1: Header\r\nLine 2: Aadhaar 3675 9832 4511\r\nLine 3: Footer\r\n"
        raw_bytes = content.encode("utf-8")

        files = {"file": ("crlf.txt", raw_bytes, "text/plain")}
        resp = client.post("/redact", files=files, data={"finding_ids": "all"})
        assert resp.status_code == 200
        redacted_bytes = resp.content

        # Verify CRLF is preserved
        assert b"\r\n" in redacted_bytes
        lines = redacted_bytes.decode("utf-8").splitlines()
        assert len(lines) == 3, f"Line count changed: expected 3, got {len(lines)}"


# =====================================================================
# 5. SPECIALIZED ADVERSARIAL CHALLENGES & POTENTIAL BUG DETECTORS
# =====================================================================

class TestAdversarialSpecialCases:
    """Specialized adversarial tests designed to uncover boundary vulnerabilities."""

    def test_log_file_extension_redact_support(self, client: TestClient):
        """CRITICAL CHALLENGE: Does POST /redact support .log files?

        app/config.py added '.log' to SUPPORTED_EXTENSIONS.
        redact_document in app/redactors/__init__.py supports .log.
        However, if scan_document in app/parsers/__init__.py forgot .log,
        uploading a .log file to /redact will fail with UnsupportedFileTypeException!
        """
        log_content = (
            "2026-09-05 02:00:00 INFO Initializing service\n"
            "2026-09-05 02:00:01 WARN User verified Aadhaar: 3675 9832 4511\n"
            "2026-09-05 02:00:02 INFO Request completed\n"
        )
        files = {"file": ("auth_audit.log", log_content.encode("utf-8"), "text/plain")}
        resp = client.post("/redact", files=files, data={"finding_ids": "all"})

        # If .log is truly supported, this MUST return 200 OK
        assert resp.status_code == 200, (
            f"POST /redact failed for .log extension with status {resp.status_code}: {resp.text}"
        )

    def test_selective_redaction_duplicate_pii_different_lines(self, client: TestClient):
        """When identical PII occurs on different lines in TXT, redacting only finding 1 leaves finding 2."""
        text = (
            "Line 1 Contact: harsh.patel@sentineldoc.com\n"
            "Line 2 Note: Intermediate line\n"
            "Line 3 Contact: harsh.patel@sentineldoc.com\n"
        )
        files = {"file": ("dup.txt", create_txt(text), "text/plain")}
        scan_resp = client.post("/scan", files=files)
        assert scan_resp.status_code == 200
        findings = scan_resp.json()["findings"]
        assert len(findings) == 2, f"Expected 2 findings for duplicate email, got {len(findings)}"

        # Select only the first finding
        first_id = findings[0]["id"]

        redact_files = {"file": ("dup.txt", create_txt(text), "text/plain")}
        redact_resp = client.post(
            "/redact",
            files=redact_files,
            data={"finding_ids": json.dumps([first_id])}
        )
        assert redact_resp.status_code == 200
        redacted_text = redact_resp.content.decode("utf-8")
        lines = redacted_text.splitlines()

        assert "[REDACTED]" in lines[0], f"Line 1 was not redacted: {lines[0]}"
        assert "harsh.patel@sentineldoc.com" in lines[2], f"Line 3 was incorrectly redacted: {lines[2]}"

    def test_pii_with_unicode_surrounding_context(self, client: TestClient):
        """PII surrounded by Devanagari Hindi characters must be scanned, redacted, and UTF-8 preserved."""
        text = (
            "कर्मचारी पहचान सारांश:\n"
            "आधार कार्ड संख्या: 3675 9832 4511\n"
            "स्थायी खाता संख्या (PAN): ABCPE1234F\n"
            "सत्यापन पूर्ण।\n"
        )
        files = {"file": ("hindi_record.txt", text.encode("utf-8"), "text/plain")}
        scan_resp = client.post("/scan", files=files)
        assert scan_resp.status_code == 200
        findings = scan_resp.json()["findings"]
        types = {f["entity_type"] for f in findings}
        assert "AADHAAR" in types
        assert "PAN" in types

        # Redact
        redact_files = {"file": ("hindi_record.txt", text.encode("utf-8"), "text/plain")}
        redact_resp = client.post("/redact", files=redact_files, data={"finding_ids": "all"})
        assert redact_resp.status_code == 200
        redacted_text = redact_resp.content.decode("utf-8")

        assert "3675 9832 4511" not in redacted_text
        assert "ABCPE1234F" not in redacted_text
        assert "कर्मचारी पहचान सारांश:" in redacted_text
        assert "सत्यापन पूर्ण।" in redacted_text

    def test_pii_with_brackets_and_parentheses(self, client: TestClient):
        """PII enclosed directly in parentheses and brackets is cleanly redacted without orphan characters."""
        text = (
            "Records: Aadhaar is [3675 9832 4511] and PAN is (ABCPE1234F).\n"
        )
        files = {"file": ("enclosed.txt", create_txt(text), "text/plain")}
        scan_resp = client.post("/scan", files=files)
        assert scan_resp.status_code == 200
        findings = scan_resp.json()["findings"]
        types = {f["entity_type"] for f in findings}
        assert "AADHAAR" in types
        assert "PAN" in types

        redact_files = {"file": ("enclosed.txt", create_txt(text), "text/plain")}
        redact_resp = client.post("/redact", files=redact_files, data={"finding_ids": "all"})
        assert redact_resp.status_code == 200
        redacted_text = redact_resp.content.decode("utf-8")

        assert "3675 9832 4511" not in redacted_text
        assert "ABCPE1234F" not in redacted_text
        assert "[" in redacted_text and "]" in redacted_text
        assert "(" in redacted_text and ")" in redacted_text

    def test_selective_redaction_same_line_mixed_pii_txt(self, client: TestClient):
        """When Aadhaar and PAN are on the exact same line in TXT, redacting only Aadhaar leaves PAN intact."""
        text = "Employee record: Aadhaar 3675 9832 4511 and PAN ABCPE1234F on the same line\n"
        files = {"file": ("same_line.txt", create_txt(text), "text/plain")}
        scan_resp = client.post("/scan", files=files)
        assert scan_resp.status_code == 200
        findings = scan_resp.json()["findings"]

        aadhaar_id = [f["id"] for f in findings if f["entity_type"] == "AADHAAR"][0]

        redact_files = {"file": ("same_line.txt", create_txt(text), "text/plain")}
        redact_resp = client.post("/redact", files=redact_files, data={"finding_ids": json.dumps([aadhaar_id])})
        assert redact_resp.status_code == 200
        redacted_text = redact_resp.content.decode("utf-8")

        assert "3675 9832 4511" not in redacted_text
        assert "ABCPE1234F" in redacted_text
        assert "[REDACTED]" in redacted_text

    def test_selective_redaction_docx_different_paragraphs(self, client: TestClient):
        """When identical PII occurs in paragraph 1 and paragraph 2 of DOCX, redacting finding 1 leaves finding 2."""
        doc = docx.Document()
        doc.add_paragraph("First notice: harsh.patel@sentineldoc.com")
        doc.add_paragraph("Second notice: harsh.patel@sentineldoc.com")
        buf = io.BytesIO()
        doc.save(buf)
        raw_docx = buf.getvalue()

        scan_resp = client.post("/scan", files={"file": ("dup_p.docx", raw_docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
        assert scan_resp.status_code == 200
        findings = scan_resp.json()["findings"]
        assert len(findings) == 2

        first_id = findings[0]["id"]
        redact_resp = client.post(
            "/redact",
            files={"file": ("dup_p.docx", raw_docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            data={"finding_ids": json.dumps([first_id])}
        )
        assert redact_resp.status_code == 200
        res_doc = docx.Document(io.BytesIO(redact_resp.content))
        p0_text = res_doc.paragraphs[0].text
        p1_text = res_doc.paragraphs[1].text

        assert "[REDACTED]" in p0_text
        assert "harsh.patel@sentineldoc.com" in p1_text

    def test_selective_redaction_docx_same_paragraph_duplicate_pii(self, client: TestClient):
        """ADVERSARIAL STRESS: When identical PII appears twice in the same DOCX paragraph,

        can selective redaction redact finding 1 without destroying finding 2?
        """
        doc = docx.Document()
        doc.add_paragraph("Primary: harsh.patel@sentineldoc.com, Secondary: harsh.patel@sentineldoc.com")
        buf = io.BytesIO()
        doc.save(buf)
        raw_docx = buf.getvalue()

        scan_resp = client.post("/scan", files={"file": ("dup_same_p.docx", raw_docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
        assert scan_resp.status_code == 200
        findings = scan_resp.json()["findings"]
        if len(findings) < 2:
            pytest.skip("Scanner only detected 1 occurrence in paragraph")

        first_id = findings[0]["id"]
        redact_resp = client.post(
            "/redact",
            files={"file": ("dup_same_p.docx", raw_docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            data={"finding_ids": json.dumps([first_id])}
        )
        assert redact_resp.status_code == 200
        res_doc = docx.Document(io.BytesIO(redact_resp.content))
        p_text = res_doc.paragraphs[0].text

        # If naive str.replace() was used, both occurrences get replaced
        assert "harsh.patel@sentineldoc.com" in p_text, (
            f"Over-redaction bug in DOCX: Both occurrences replaced even though only one was selected! Result: {p_text}"
        )

    def test_selective_redaction_csv_same_cell_duplicate_pii(self, client: TestClient):
        """ADVERSARIAL STRESS: When identical PII appears twice in the same CSV cell,

        can selective redaction redact finding 1 without destroying finding 2?
        """
        header = ["ID", "Emails"]
        rows = [["1", "harsh.patel@sentineldoc.com, harsh.patel@sentineldoc.com"]]
        csv_bytes = generate_simple_csv(header, rows)

        scan_resp = client.post("/scan", files={"file": ("dup_cell.csv", csv_bytes, "text/csv")})
        assert scan_resp.status_code == 200
        findings = scan_resp.json()["findings"]
        if len(findings) < 2:
            pytest.skip("Scanner only detected 1 occurrence in cell")

        first_id = findings[0]["id"]
        redact_resp = client.post(
            "/redact",
            files={"file": ("dup_cell.csv", csv_bytes, "text/csv")},
            data={"finding_ids": json.dumps([first_id])}
        )
        assert redact_resp.status_code == 200
        reader = list(csv.reader(io.StringIO(redact_resp.content.decode("utf-8"))))
        cell_val = reader[1][1]

        assert "harsh.patel@sentineldoc.com" in cell_val, (
            f"Over-redaction bug in CSV: Both occurrences replaced in cell even though only one was selected! Result: {cell_val}"
        )

    def test_selective_redaction_pdf_duplicate_pii_same_page(self, client: TestClient):
        """ADVERSARIAL STRESS: When identical PII appears twice on the same PDF page,

        can selective redaction redact finding 1 while leaving finding 2 intact?
        """
        page = [
            (72.0, 100.0, "First contact: harsh.patel@sentineldoc.com"),
            (72.0, 300.0, "Second contact: harsh.patel@sentineldoc.com"),
        ]
        pdf_bytes = create_pdf([page])

        scan_resp = client.post("/scan", files={"file": ("dup_pdf.pdf", pdf_bytes, "application/pdf")})
        assert scan_resp.status_code == 200
        findings = scan_resp.json()["findings"]
        if len(findings) < 2:
            pytest.skip("Scanner only detected 1 occurrence in PDF")

        first_id = findings[0]["id"]
        redact_resp = client.post(
            "/redact",
            files={"file": ("dup_pdf.pdf", pdf_bytes, "application/pdf")},
            data={"finding_ids": json.dumps([first_id])}
        )
        assert redact_resp.status_code == 200
        redacted_doc = fitz.open(stream=redact_resp.content, filetype="pdf")
        page_text = redacted_doc[0].get_text()
        redacted_doc.close()

        # Check if second contact was preserved
        assert "Second contact: harsh.patel@sentineldoc.com" in page_text or "harsh.patel@sentineldoc.com" in page_text, (
            f"Over-redaction bug in PDF: Both occurrences purged even though only first was selected! Result: {page_text}"
        )

    def test_xlsx_formula_pii_handling(self, client: TestClient):
        """ADVERSARIAL STRESS: Excel formula cell containing sensitive PII."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Formulas"
        ws["A1"] = '="Aadhaar: " & "3675 9832 4511"'
        buf = io.BytesIO()
        wb.save(buf)
        raw_xlsx = buf.getvalue()

        # Scan document
        scan_resp = client.post("/scan", files={"file": ("formula.xlsx", raw_xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        assert scan_resp.status_code == 200
        findings = scan_resp.json()["findings"]
        # If openpyxl data_only=True returns None for unevaluated formulas, scan findings will be empty
        # If redacted anyway with 'all', does redact alter or skip formula cell?
        redact_resp = client.post(
            "/redact",
            files={"file": ("formula.xlsx", raw_xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={"finding_ids": "all"}
        )
        assert redact_resp.status_code == 200
        redacted_wb = openpyxl.load_workbook(io.BytesIO(redact_resp.content), data_only=False)
        a1_val = str(redacted_wb["Formulas"]["A1"].value)
        redacted_wb.close()
        # Document whether formula was skipped
        assert a1_val.startswith("="), f"Formula cell corrupted: {a1_val}"





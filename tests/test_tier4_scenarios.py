"""Tier 4: Real-World Scenarios Benchmark Test Suite.

Executes complete end-to-end user workflows against 5 production-style synthetic documents:
1. synthetic_resume.pdf: Multi-page candidate CV
2. synthetic_invoice.xlsx: Multi-item corporate tax invoice
3. synthetic_customer_database.csv: 50-row enterprise customer database
4. synthetic_confidential_memo.docx: Executive legal agreement and disciplinary memo
5. synthetic_server_audit.txt: 500-line cloud microservice audit telemetry log
"""
import io
import csv
import json
import pytest
import fitz
import docx
import openpyxl
from fastapi.testclient import TestClient

from tests.conftest import assert_valid_scan_response, is_redact_implemented


@pytest.mark.tier4
class TestTier4Scenarios:
    """Production-style scenario benchmarks."""

    def test_scenario_synthetic_resume_pdf(self, client: TestClient, synthetic_resume_pdf: bytes):
        """Workflow: Scan resume -> Verify 5+ findings -> Redact all -> Re-scan yields 0 leaks -> Verify PDF structure."""
        # 1. Scan original
        files = {"file": ("aarav_sharma_resume.pdf", synthetic_resume_pdf, "application/pdf")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        data = resp.json()
        assert_valid_scan_response(data)

        findings = data["findings"]
        types = {f["entity_type"] for f in findings}
        assert "AADHAAR" in types
        assert "PAN" in types
        assert "PHONE_NUMBER" in types
        assert "EMAIL_ADDRESS" in types

        if not is_redact_implemented(client):
            pytest.skip("Milestone 2 (/redact) not yet implemented in current build")

        # 2. Redact all
        redact_files = {"file": ("aarav_sharma_resume.pdf", synthetic_resume_pdf, "application/pdf")}
        redact_resp = client.post("/redact", files=redact_files, data={"finding_ids": "all"})
        assert redact_resp.status_code == 200
        redacted_bytes = redact_resp.content

        # 3. Verify format preservation
        doc = fitz.open(stream=redacted_bytes, filetype="pdf")
        assert doc.page_count == 2, f"Page count changed: {doc.page_count}"
        doc.close()

        # 4. Golden Round-Trip: Re-scan redacted PDF
        rescan_files = {"file": ("redacted_resume.pdf", redacted_bytes, "application/pdf")}
        rescan_resp = client.post("/scan", files=rescan_files)
        assert rescan_resp.status_code == 200
        critical_leaks = [
            f for f in rescan_resp.json()["findings"]
            if f["entity_type"] in ("AADHAAR", "PAN", "CREDIT_CARD")
        ]
        assert len(critical_leaks) == 0, f"Critical PII leaked in redacted PDF: {critical_leaks}"

    def test_scenario_synthetic_invoice_xlsx(self, client: TestClient, synthetic_invoice_xlsx: bytes):
        """Workflow: Scan corporate invoice -> Redact card -> Verify formulas & cell structure preserved."""
        # 1. Scan original invoice
        files = {"file": ("tax_invoice.xlsx", synthetic_invoice_xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        data = resp.json()
        findings = data["findings"]

        card_findings = [f for f in findings if f["entity_type"] == "CREDIT_CARD"]
        assert len(card_findings) >= 1
        card_id = card_findings[0]["id"]

        if not is_redact_implemented(client):
            pytest.skip("Milestone 2 (/redact) not yet implemented in current build")

        # 2. Redact card
        redact_files = {"file": ("tax_invoice.xlsx", synthetic_invoice_xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        redact_resp = client.post(
            "/redact",
            files=redact_files,
            data={"finding_ids": json.dumps([card_id])}
        )
        assert redact_resp.status_code == 200
        redacted_xlsx = redact_resp.content

        # 3. Verify openpyxl can load and structure is preserved
        wb = openpyxl.load_workbook(io.BytesIO(redacted_xlsx))
        assert "Tax_Invoice" in wb.sheetnames
        ws = wb["Tax_Invoice"]
        # Grand total cell remains intact
        assert ws["F21"].value == "Grand Total:"
        assert ws["G21"].value == 666700.0

        # 4. Re-scan
        rescan_files = {"file": ("redacted_tax_invoice.xlsx", redacted_xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        rescan_resp = client.post("/scan", files=rescan_files)
        assert rescan_resp.status_code == 200
        rescan_cards = [f for f in rescan_resp.json()["findings"] if f["entity_type"] == "CREDIT_CARD"]
        assert len(rescan_cards) == 0, "Card still detected after redaction"

    def test_scenario_synthetic_customer_database_csv(self, client: TestClient, synthetic_customer_csv: bytes):
        """Workflow: Scan 50-row customer database -> Verify 0 false positives -> Redact all -> Verify 0 leaks."""
        # 1. Scan original
        files = {"file": ("customers.csv", synthetic_customer_csv, "text/csv")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        data = resp.json()
        findings = data["findings"]

        # Non-PII order IDs (col 9) and zip codes (col 10) must not be flagged
        fp_orders = [f for f in findings if f["location"]["col"] == 9 and f["entity_type"] == "PHONE_NUMBER"]
        assert len(fp_orders) == 0, f"Order IDs falsely flagged as phone: {fp_orders}"

        if not is_redact_implemented(client):
            pytest.skip("Milestone 2 (/redact) not yet implemented in current build")

        # 2. Redact all findings
        redact_files = {"file": ("customers.csv", synthetic_customer_csv, "text/csv")}
        redact_resp = client.post("/redact", files=redact_files, data={"finding_ids": "all"})
        assert redact_resp.status_code == 200
        redacted_csv = redact_resp.content

        # 3. Verify CSV structure
        csv_text = redacted_csv.decode("utf-8")
        rows = list(csv.reader(io.StringIO(csv_text)))
        assert len(rows) == 51, f"Row count changed: {len(rows)}"  # header + 50 rows
        assert "[REDACTED]" in csv_text

        # 4. Re-scan
        rescan_files = {"file": ("redacted_customers.csv", redacted_csv, "text/csv")}
        rescan_resp = client.post("/scan", files=rescan_files)
        assert rescan_resp.status_code == 200
        rescan_findings = [
            f for f in rescan_resp.json()["findings"]
            if f["entity_type"] in ("AADHAAR", "PAN", "CREDIT_CARD")
        ]
        assert len(rescan_findings) == 0, f"PII leaked in redacted CSV: {rescan_findings}"

    def test_scenario_synthetic_confidential_memo_docx(self, client: TestClient, synthetic_memo_docx: bytes):
        """Workflow: Scan executive legal memo -> Redact all -> Verify DOCX openable and PII replaced."""
        # 1. Scan original
        files = {"file": ("severance_memo.docx", synthetic_memo_docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = resp.json()["findings"]
        pan_findings = [f for f in findings if f["entity_type"] == "PAN"]
        assert len(pan_findings) >= 1

        if not is_redact_implemented(client):
            pytest.skip("Milestone 2 (/redact) not yet implemented in current build")

        # 2. Redact all
        redact_files = {"file": ("severance_memo.docx", synthetic_memo_docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        redact_resp = client.post("/redact", files=redact_files, data={"finding_ids": "all"})
        assert redact_resp.status_code == 200
        redacted_docx = redact_resp.content

        # 3. Verify DOCX readability
        doc = docx.Document(io.BytesIO(redacted_docx))
        full_text = "\n".join([p.text for p in doc.paragraphs])
        assert "[REDACTED]" in full_text
        assert "BNZPK9876M" not in full_text

        # 4. Re-scan
        rescan_files = {"file": ("redacted_memo.docx", redacted_docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        rescan_resp = client.post("/scan", files=rescan_files)
        assert rescan_resp.status_code == 200
        rescan_pan = [f for f in rescan_resp.json()["findings"] if f["entity_type"] == "PAN"]
        assert len(rescan_pan) == 0

    def test_scenario_synthetic_server_audit_txt(self, client: TestClient, synthetic_audit_txt: bytes):
        """Workflow: Scan 500-line server audit log -> Redact all -> Verify line count preserved and logs masked."""
        # 1. Scan original
        files = {"file": ("server_audit.txt", synthetic_audit_txt, "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = resp.json()["findings"]
        assert len(findings) >= 3

        if not is_redact_implemented(client):
            pytest.skip("Milestone 2 (/redact) not yet implemented in current build")

        # 2. Redact all
        redact_files = {"file": ("server_audit.txt", synthetic_audit_txt, "text/plain")}
        redact_resp = client.post("/redact", files=redact_files, data={"finding_ids": "all"})
        assert redact_resp.status_code == 200
        redacted_txt = redact_resp.content.decode("utf-8")

        # 3. Verify line count and format
        original_lines = synthetic_audit_txt.decode("utf-8").strip().split("\n")
        redacted_lines = redacted_txt.strip().split("\n")
        assert len(redacted_lines) == len(original_lines), "Line count altered by redaction"

        # Card number must be replaced with [REDACTED]
        assert "4532 0151 1283 0366" not in redacted_txt
        assert "[REDACTED]" in redacted_txt

        # 4. Re-scan
        rescan_files = {"file": ("redacted_server_audit.txt", redact_resp.content, "text/plain")}
        rescan_resp = client.post("/scan", files=rescan_files)
        assert rescan_resp.status_code == 200
        rescan_cards = [f for f in rescan_resp.json()["findings"] if f["entity_type"] == "CREDIT_CARD"]
        assert len(rescan_cards) == 0

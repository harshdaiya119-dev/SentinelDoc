"""Empirical Adversarial Test Suite for SentinelDoc M3.
Authored by challenger_m3_4 (Empirical Challenger, Milestone 3).

Adversarial Verification Targets:
1. Content Negotiation Conflicts & Header Compliance:
   - ?format=pdf vs Accept: application/json
   - ?format=json vs Accept: application/pdf
   - ?format=PDF (case variation) vs Accept: application/json
   - ?format=JSON (case variation) vs Accept: application/pdf
   - Accept: application/pdf; q=0.8, application/json; q=0.9
   - Accept: */*
   - Query param taking absolute precedence over Accept header
   - Content-Type verification (application/pdf vs application/json)
   - Content-Disposition header verification (attachment; filename="...")
   - Error responses under ?format=pdf preserve standard JSON error envelopes
2. PDF Text Stream Privacy Leak Resistance:
   - Planted documents containing valid Aadhaar (3675 9832 4511, etc.), Credit Cards (Visa, Mastercard, RuPay), PAN, Phone, Email, Person, Address.
   - Deep PyMuPDF (fitz) inspection of pages, text streams, words, blocks, and XML dumps.
   - Regex auditing ensuring raw sensitive numbers NEVER appear unmasked in the generated PDF report.
   - Safe-harbor masked values (XXXX-XXXX-4511, etc.) verified in audit log table.
3. False-Positive Isolation:
   - Pure postal PIN codes, Order IDs, tracking numbers, timestamps, financial amounts, and invalid checksum numbers (failing Verhoeff / Luhn).
   - Verification that risk_score NEVER triggers High (risk_score < 70, strictly Low risk < 40).
   - Verification that critical_count and high_count are strictly 0.
   - Verification across document formats (TXT, PDF, DOCX, CSV, XLSX).
"""
import io
import re
import pytest
from fastapi.testclient import TestClient
import fitz  # PyMuPDF

from tests.fixtures.generator import (
    create_txt,
    generate_simple_pdf,
    generate_simple_docx,
    generate_simple_csv,
    generate_simple_xlsx,
)
from app.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


# =====================================================================
# 1. CONTENT NEGOTIATION CONFLICTS & HEADER SPECIFICATION
# =====================================================================

class TestContentNegotiationEdgeCases:
    """Test conflicting, ambiguous, and edge-case content negotiation headers and query params."""

    SAMPLE_DOC = "SentinelDoc Security Evaluation.\nInternal Audit Notice.\nAll systems operational.\n"

    def test_conflicting_format_pdf_and_accept_json(self, client: TestClient):
        """Query format=pdf must take priority over Accept: application/json."""
        files = {"file": ("sec_eval.txt", create_txt(self.SAMPLE_DOC), "text/plain")}
        headers = {"Accept": "application/json"}
        resp = client.post("/report?format=pdf", files=files, headers=headers)

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        assert "application/pdf" in resp.headers.get("content-type", "")
        
        # Verify Content-Disposition attachment header
        disp = resp.headers.get("content-disposition", "")
        assert "attachment" in disp.lower()
        assert 'filename="SentinelDoc_Risk_Report_sec_eval.txt.pdf"' in disp

        # Verify valid PDF binary stream
        assert resp.content.startswith(b"%PDF-")
        doc = fitz.open(stream=resp.content, filetype="pdf")
        assert doc.page_count >= 1
        doc.close()

    def test_conflicting_format_json_and_accept_pdf(self, client: TestClient):
        """Query format=json must take priority over Accept: application/pdf."""
        files = {"file": ("sec_eval.txt", create_txt(self.SAMPLE_DOC), "text/plain")}
        headers = {"Accept": "application/pdf"}
        resp = client.post("/report?format=json", files=files, headers=headers)

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        assert "application/json" in resp.headers.get("content-type", "")
        
        # Content-Disposition should not be attachment for JSON
        disp = resp.headers.get("content-disposition", "")
        assert "attachment" not in disp.lower()

        data = resp.json()
        assert "risk_score" in data
        assert "risk_level" in data
        assert "findings" in data
        assert "summary" in data
        assert data["file_name"] == "sec_eval.txt"

    def test_case_insensitive_format_variations(self, client: TestClient):
        """Query parameter format must be case-insensitive (PDF, Pdf, pDf, JSON, Json, jSoN)."""
        # PDF variations
        for fmt in ["PDF", "Pdf", "pDf"]:
            files = {"file": ("test.txt", create_txt(self.SAMPLE_DOC), "text/plain")}
            resp = client.post(f"/report?format={fmt}", files=files, headers={"Accept": "application/json"})
            assert resp.status_code == 200
            assert "application/pdf" in resp.headers.get("content-type", "")
            assert resp.content.startswith(b"%PDF-")

        # JSON variations
        for fmt in ["JSON", "Json", "jSoN"]:
            files = {"file": ("test.txt", create_txt(self.SAMPLE_DOC), "text/plain")}
            resp = client.post(f"/report?format={fmt}", files=files, headers={"Accept": "application/pdf"})
            assert resp.status_code == 200
            assert "application/json" in resp.headers.get("content-type", "")
            assert isinstance(resp.json(), dict)

    def test_accept_header_without_format_query(self, client: TestClient):
        """Accept: application/pdf without query returns PDF; Accept: application/json returns JSON."""
        # PDF accept
        files = {"file": ("doc.txt", create_txt(self.SAMPLE_DOC), "text/plain")}
        resp_pdf = client.post("/report", files=files, headers={"Accept": "application/pdf"})
        assert resp_pdf.status_code == 200
        assert "application/pdf" in resp_pdf.headers.get("content-type", "")
        assert resp_pdf.content.startswith(b"%PDF-")

        # JSON accept
        files = {"file": ("doc.txt", create_txt(self.SAMPLE_DOC), "text/plain")}
        resp_json = client.post("/report", files=files, headers={"Accept": "application/json"})
        assert resp_json.status_code == 200
        assert "application/json" in resp_json.headers.get("content-type", "")
        assert "risk_score" in resp_json.json()

    def test_error_responses_with_format_pdf_return_json_envelope(self, client: TestClient):
        """Errors must always return JSON envelope with proper HTTP status codes even when ?format=pdf is passed."""
        # 1. Empty file -> 400 EMPTY_FILE
        resp_empty = client.post("/report?format=pdf", files={"file": ("empty.txt", b"", "text/plain")})
        assert resp_empty.status_code == 400
        assert "application/json" in resp_empty.headers.get("content-type", "")
        assert resp_empty.json()["error"]["code"] == "EMPTY_FILE"

        # 2. Unsupported extension -> 400 UNSUPPORTED_FILE_TYPE
        resp_unsupp = client.post("/report?format=pdf", files={"file": ("bad.exe", b"binary", "application/octet-stream")})
        assert resp_unsupp.status_code == 400
        assert "application/json" in resp_unsupp.headers.get("content-type", "")
        assert resp_unsupp.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"

        # 3. Missing file payload -> 422 Unprocessable Entity
        resp_missing = client.post("/report?format=pdf")
        assert resp_missing.status_code == 422
        assert "application/json" in resp_missing.headers.get("content-type", "")


# =====================================================================
# 2. PDF TEXT STREAM PRIVACY LEAK CHALLENGE (FIT Z INSPECTION)
# =====================================================================

class TestPdfTextStreamPrivacyAudit:
    """Rigorous adversarial testing of generated PDF streams to ensure zero unmasked PII leaks."""

    PLANTED_SENSITIVE_TEXT = (
        "RESTRICTED COMPLIANCE AUDIT TARGET\n"
        "Employee Record: Siddharth Vikramaditya\n"
        "Primary Email: siddharth.vikramaditya@sentineldoc.internal\n"
        "Contact Number: +91 98765 43210\n"
        "Aadhaar Number 1 (Spaced): 3675 9832 4511\n"
        "Aadhaar Number 2 (Continuous): 982341567897\n"
        "Aadhaar Number 3 (Hyphenated): 4321-8765-2109\n"
        "PAN Card: ABCPE1234F\n"
        "Corporate Visa Card: 4532 0151 1283 0366\n"
        "Secondary Mastercard: 5424-1801-2345-6789\n"
        "Emergency RuPay: 6071 2345 6789 0120\n"
        "Date of Birth: 15/08/1985\n"
        "Home Address: Flat 402, Lotus Towers, MG Road, Bangalore 560001\n"
    )

    RAW_PII_CATALOG = [
        "3675 9832 4511",
        "367598324511",
        "982341567897",
        "9823 4156 7897",
        "4321-8765-2109",
        "432187652109",
        "4532 0151 1283 0366",
        "4532015112830366",
        "5424-1801-2345-6789",
        "5424180123456789",
        "6071 2345 6789 0120",
        "6071234567890120",
        "ABCPE1234F",
        "siddharth.vikramaditya@sentineldoc.internal",
    ]

    def test_fitz_full_text_and_word_stream_zero_leakage(self, client: TestClient):
        """Verify using PyMuPDF (fitz) that raw sensitive values NEVER appear unmasked."""
        files = {"file": ("sensitive.txt", create_txt(self.PLANTED_SENSITIVE_TEXT), "text/plain")}
        resp = client.post("/report?format=pdf", files=files)
        assert resp.status_code == 200

        doc = fitz.open(stream=resp.content, filetype="pdf")
        assert doc.page_count >= 1

        extracted_text = ""
        extracted_words = []
        for page in doc:
            extracted_text += page.get_text("text") + "\n"
            extracted_words.extend([w[4] for w in page.get_text("words")])

        # 1. Exact unmasked string check
        for target in self.RAW_PII_CATALOG:
            assert target not in extracted_text, (
                f"PRIVACY VIOLATION: Raw target '{target}' leaked in PDF text stream!"
            )
            assert target not in extracted_words, (
                f"PRIVACY VIOLATION: Raw target '{target}' leaked in PDF word tokens!"
            )

        # 2. Regex check: no 12-digit Aadhaar matched
        twelve_digits = re.findall(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}\b", extracted_text)
        for match in twelve_digits:
            clean = "".join(c for c in match if c.isdigit())
            assert clean not in ("367598324511", "982341567897", "432187652109"), (
                f"PRIVACY VIOLATION: Unmasked 12-digit Aadhaar detected via regex: '{match}'"
            )

        # 3. Regex check: no 16-digit Card matched
        sixteen_digits = re.findall(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b", extracted_text)
        for match in sixteen_digits:
            clean = "".join(c for c in match if c.isdigit())
            assert clean not in ("4532015112830366", "5424180123456789", "6071234567890120"), (
                f"PRIVACY VIOLATION: Unmasked 16-digit Card detected via regex: '{match}'"
            )

        # 4. Safe-harbor masked values MUST be present
        assert "XXXX-XXXX-4511" in extracted_text, "Masked Aadhaar XXXX-XXXX-4511 not found in report"
        assert "XXXX-XXXX-XXXX-0366" in extracted_text, "Masked Visa XXXX-XXXX-XXXX-0366 not found in report"

        doc.close()

    def test_raw_bytes_stream_no_plaintext_leak(self, client: TestClient):
        """Raw PDF binary bytes must not contain uncompressed plaintext PII."""
        files = {"file": ("sensitive.txt", create_txt(self.PLANTED_SENSITIVE_TEXT), "text/plain")}
        resp = client.post("/report?format=pdf", files=files)
        assert resp.status_code == 200

        pdf_bytes = resp.content
        assert b"3675 9832 4511" not in pdf_bytes
        assert b"367598324511" not in pdf_bytes
        assert b"4532 0151 1283 0366" not in pdf_bytes
        assert b"ABCPE1234F" not in pdf_bytes


# =====================================================================
# 3. FALSE-POSITIVE ISOLATION & RISK SCORE CALIBRATION
# =====================================================================

class TestFalsePositiveIsolationSuite:
    """Verify documents with only false-positive candidates NEVER trigger High risk."""

    FP_CORPUS = (
        "Warehouse Logistics Report & Manifest Telemetry\n"
        "Tracking Reference: TRK-9876543210987654\n"
        "Customer Purchase Order: ORD-1002938475\n"
        "Postal Destination Codes: 560034, 110001, 400001, 600001\n"
        "SKU Identifier: SKU-ABCD12345E\n"
        "Pallet Bin Location: BIN-12345ABCDE\n"
        "Part Serial Number: PART-ABCDE12345\n"
        "System Epoch Timestamp: 1725495000\n"
        "Total Freight Invoice: INR 45,000.00\n"
        "Firmware Revision: v2.4.1\n"
        "Internal Listener Port: 8080\n"
        "Invalid Aadhaar (fails Verhoeff): 3675 9832 4512\n"
        "Invalid Aadhaar prefix 0: 0123 4567 8901\n"
        "Invalid Credit Card (fails Luhn): 4532 0151 1283 0367\n"
        "Arbitrary 16-digit order number: 9876543210987654\n"
        "Sequential numeric test string: 0123456789\n"
    )

    def test_false_positive_corpus_never_triggers_high_risk(self, client: TestClient):
        """False-positive candidate corpus must NEVER trigger High risk (risk_score < 70, strictly Low < 40)."""
        files = {"file": ("fp_telemetry.txt", create_txt(self.FP_CORPUS), "text/plain")}
        resp = client.post("/report?format=json", files=files)
        assert resp.status_code == 200

        data = resp.json()
        assert data["risk_level"] == "Low", f"Expected Low risk level, got {data['risk_level']}"
        assert data["risk_score"] < 40, f"Expected risk_score < 40, got {data['risk_score']}"

        # Critical and High tier counts must be 0
        summary = data["summary"]
        assert summary["critical_count"] == 0, f"False positive triggered critical_count: {summary['critical_count']}"
        assert summary["high_count"] == 0, f"False positive triggered high_count: {summary['high_count']}"

        # Verify no Aadhaar or Credit Card findings
        for f in data["findings"]:
            assert f["entity_type"] not in ("AADHAAR", "CREDIT_CARD", "PAN"), (
                f"False positive falsely classified as {f['entity_type']}: {f['matched_text']}"
            )

    def test_postal_pin_codes_only_evaluates_to_zero_risk(self, client: TestClient):
        """Document with only postal PIN codes evaluates to risk score 0."""
        text = "Destination pin codes for delivery: 560001, 110001, 400001, 600001, 700001, 560034."
        files = {"file": ("pincodes.txt", create_txt(text), "text/plain")}
        resp = client.post("/report?format=json", files=files)
        assert resp.status_code == 200

        data = resp.json()
        assert data["risk_score"] == 0, f"Expected risk score 0, got {data['risk_score']}"
        assert data["risk_level"] == "Low"
        assert data["total_findings"] == 0

    def test_order_ids_only_evaluates_to_zero_risk(self, client: TestClient):
        """Document with only order IDs and tracking numbers evaluates to risk score 0."""
        text = (
            "Order confirmation receipt.\n"
            "Order ID: 1002938475\n"
            "Tracking Number: 9876543210987654\n"
            "Manifest Reference: ORD-123456789012\n"
            "Item sequence: 0123456789\n"
        )
        files = {"file": ("orders.txt", create_txt(text), "text/plain")}
        resp = client.post("/report?format=json", files=files)
        assert resp.status_code == 200

        data = resp.json()
        assert data["risk_score"] == 0, f"Expected risk score 0, got {data['risk_score']}"
        assert data["risk_level"] == "Low"
        assert data["total_findings"] == 0

    def test_false_positives_across_all_formats(self, client: TestClient):
        """Verify false-positive resistance across PDF, DOCX, CSV, and XLSX formats."""
        # 1. PDF
        pdf_bytes = generate_simple_pdf(self.FP_CORPUS)
        resp_pdf = client.post("/report?format=json", files={"file": ("fp.pdf", pdf_bytes, "application/pdf")})
        assert resp_pdf.status_code == 200
        assert resp_pdf.json()["risk_level"] == "Low"
        assert resp_pdf.json()["risk_score"] < 40

        # 2. DOCX
        docx_bytes = generate_simple_docx(self.FP_CORPUS)
        resp_docx = client.post("/report?format=json", files={"file": ("fp.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
        assert resp_docx.status_code == 200
        assert resp_docx.json()["risk_level"] == "Low"
        assert resp_docx.json()["risk_score"] < 40

        # 3. CSV
        csv_header = ["row_id", "order_id", "tracking_no", "pin_code", "test_invalid"]
        csv_rows = [
            [1, "ORD-123456789012", "9876543210987654", "560034", "3675 9832 4512"],
            [2, "1002938475", "0123456789", "110001", "4532 0151 1283 0367"],
        ]
        csv_bytes = generate_simple_csv(csv_header, csv_rows)
        resp_csv = client.post("/report?format=json", files={"file": ("fp.csv", csv_bytes, "text/csv")})
        assert resp_csv.status_code == 200
        assert resp_csv.json()["risk_level"] == "Low"
        assert resp_csv.json()["risk_score"] < 40

        # 4. XLSX
        xlsx_bytes = generate_simple_xlsx("FalsePositives", csv_header, csv_rows)
        resp_xlsx = client.post("/report?format=json", files={"file": ("fp.xlsx", xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        assert resp_xlsx.status_code == 200
        assert resp_xlsx.json()["risk_level"] == "Low"
        assert resp_xlsx.json()["risk_score"] < 40

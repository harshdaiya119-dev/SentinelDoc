"""Empirical Adversarial Challenge Suite for Milestone 3 (Risk Report Generation).

Authored by challenger_m3_2 (Empirical Challenger, Milestone 3).
Adversarially challenges and empirically verifies:
1. API Contract & Content Negotiation Matrix:
   - ?format=pdf vs Accept: application/json -> Query param takes precedence, returns binary PDF.
   - ?format=json vs Accept: application/pdf -> Query param takes precedence, returns JSON ReportResponse.
   - Case-insensitivity (?format=PDF, ?format=JSON, ?format=Pdf).
   - Appropriate Content-Type (application/pdf vs application/json) and Content-Disposition headers.
   - Default fallbacks for wildcard Accept (*/*) and browser Accept headers.
   - Error requests (0-byte file, unsupported extension, missing payload) preserve JSON error envelope.
2. PDF Text Stream Privacy Leak Resistance:
   - Ingests documents with planted valid Aadhaar (3675 9832 4511, etc.), Credit Cards (Visa, Mastercard, RuPay), PAN, Phone, Email, Person, and Address.
   - PyMuPDF (fitz) deep inspection of all pages, words, and text blocks.
   - Regex scan ensuring raw 12-digit Aadhaar and raw 16-digit credit card numbers NEVER appear in the PDF text stream.
   - Verifies safe-harbor masked values appear instead.
3. False-Positive Isolation:
   - Documents with only false-positive candidates (zip codes, order IDs, invalid Verhoeff Aadhaar, invalid Luhn cards, timestamps, sequential digits).
   - Verifies risk_score is 0 (or strictly Low risk < 40), NEVER triggering High or Medium risk.
   - Verifies critical_count and high_count are 0.
   - Multi-format verification across PDF, DOCX, CSV, XLSX, and TXT.
   - Mass stress-test with 100 invalid Aadhaar/Card numbers.
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
from tests.fixtures.sample_data import FALSE_POSITIVE_16_CASES


@pytest.fixture(scope="module")
def client() -> TestClient:
    from app.main import app
    return TestClient(app)


# =====================================================================
# PART 1: CONTENT NEGOTIATION MATRIX & HEADER SPECIFICATION
# =====================================================================

class TestContentNegotiationMatrix:
    """Adversarial challenge for format query param vs Accept header matrix."""

    SAMPLE_TEXT = "Test Document for Content Negotiation.\nSubject: System Audit Log.\nStatus: Ready.\n"

    def test_format_pdf_overrides_accept_application_json(self, client: TestClient):
        """Query parameter ?format=pdf must take precedence over Accept: application/json."""
        files = {"file": ("audit_report.txt", create_txt(self.SAMPLE_TEXT), "text/plain")}
        headers = {"Accept": "application/json"}
        resp = client.post("/report?format=pdf", files=files, headers=headers)

        assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}: {resp.text}"
        
        # Verify Content-Type is strictly application/pdf
        content_type = resp.headers.get("content-type", "")
        assert "application/pdf" in content_type, f"Expected application/pdf Content-Type, got: {content_type}"

        # Verify Content-Disposition header
        disp = resp.headers.get("content-disposition", "")
        assert "attachment" in disp.lower(), f"Content-Disposition missing 'attachment': {disp}"
        assert 'filename="SentinelDoc_Risk_Report_audit_report.txt.pdf"' in disp, (
            f"Content-Disposition missing expected filename: {disp}"
        )

        # Verify binary magic bytes
        assert resp.content.startswith(b"%PDF-"), "Response binary stream does not begin with %PDF-"
        assert len(resp.content) > 1000, f"Generated PDF stream is unexpectedly small: {len(resp.content)} bytes"

    def test_format_json_overrides_accept_application_pdf(self, client: TestClient):
        """Query parameter ?format=json must take precedence over Accept: application/pdf."""
        files = {"file": ("audit_report.txt", create_txt(self.SAMPLE_TEXT), "text/plain")}
        headers = {"Accept": "application/pdf"}
        resp = client.post("/report?format=json", files=files, headers=headers)

        assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}: {resp.text}"

        # Verify Content-Type is strictly application/json
        content_type = resp.headers.get("content-type", "")
        assert "application/json" in content_type, f"Expected application/json Content-Type, got: {content_type}"

        # Verify Content-Disposition is NOT an attachment
        disp = resp.headers.get("content-disposition", "")
        assert "attachment" not in disp.lower(), f"Content-Disposition unexpectedly contains attachment: {disp}"

        # Verify response body is valid ReportResponse JSON
        data = resp.json()
        assert "risk_score" in data
        assert "risk_level" in data
        assert "findings" in data
        assert "summary" in data
        assert isinstance(data["risk_score"], int)
        assert data["file_name"] == "audit_report.txt"

    @pytest.mark.parametrize("format_val", ["PDF", "Pdf", "pDf", "pdf"])
    def test_format_pdf_case_insensitivity(self, client: TestClient, format_val: str):
        """Format parameter ?format=... should be case-insensitive for PDF."""
        files = {"file": ("case_test.txt", create_txt(self.SAMPLE_TEXT), "text/plain")}
        headers = {"Accept": "application/json"}
        resp = client.post(f"/report?format={format_val}", files=files, headers=headers)

        assert resp.status_code == 200
        assert "application/pdf" in resp.headers.get("content-type", "")
        assert resp.content.startswith(b"%PDF-")

    @pytest.mark.parametrize("format_val", ["JSON", "Json", "jSoN", "json"])
    def test_format_json_case_insensitivity(self, client: TestClient, format_val: str):
        """Format parameter ?format=... should be case-insensitive for JSON."""
        files = {"file": ("case_test.txt", create_txt(self.SAMPLE_TEXT), "text/plain")}
        headers = {"Accept": "application/pdf"}
        resp = client.post(f"/report?format={format_val}", files=files, headers=headers)

        assert resp.status_code == 200
        assert "application/json" in resp.headers.get("content-type", "")
        assert isinstance(resp.json(), dict)

    def test_accept_browser_default_returns_json(self, client: TestClient):
        """Standard browser Accept header without format query defaults to JSON ReportResponse."""
        files = {"file": ("browser_test.txt", create_txt(self.SAMPLE_TEXT), "text/plain")}
        headers = {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"}
        resp = client.post("/report", files=files, headers=headers)

        assert resp.status_code == 200
        assert "application/json" in resp.headers.get("content-type", "")
        data = resp.json()
        assert data["file_name"] == "browser_test.txt"

    def test_accept_wildcard_returns_json(self, client: TestClient):
        """Accept: */* defaults to JSON ReportResponse."""
        files = {"file": ("wildcard_test.txt", create_txt(self.SAMPLE_TEXT), "text/plain")}
        headers = {"Accept": "*/*"}
        resp = client.post("/report", files=files, headers=headers)

        assert resp.status_code == 200
        assert "application/json" in resp.headers.get("content-type", "")
        assert "risk_score" in resp.json()

    def test_accept_pdf_only_returns_pdf(self, client: TestClient):
        """Accept: application/pdf without query parameter returns PDF attachment."""
        files = {"file": ("pdf_accept.txt", create_txt(self.SAMPLE_TEXT), "text/plain")}
        headers = {"Accept": "application/pdf"}
        resp = client.post("/report", files=files, headers=headers)

        assert resp.status_code == 200
        assert "application/pdf" in resp.headers.get("content-type", "")
        assert resp.content.startswith(b"%PDF-")
        assert "attachment" in resp.headers.get("content-disposition", "").lower()

    def test_error_with_format_pdf_preserves_json_error_envelope(self, client: TestClient):
        """Error cases (empty file, unsupported file) must return JSON envelope, even with ?format=pdf."""
        # 1. Empty file
        files = {"file": ("empty.txt", b"", "text/plain")}
        resp = client.post("/report?format=pdf", files=files)
        assert resp.status_code == 400
        assert "application/json" in resp.headers.get("content-type", "")
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == "EMPTY_FILE"

        # 2. Unsupported extension
        files = {"file": ("script.sh", b"echo hello", "text/plain")}
        resp = client.post("/report?format=pdf", files=files)
        assert resp.status_code == 400
        assert "application/json" in resp.headers.get("content-type", "")
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == "UNSUPPORTED_FILE_TYPE"

        # 3. Missing file payload
        resp = client.post("/report?format=pdf")
        assert resp.status_code == 422
        assert "application/json" in resp.headers.get("content-type", "")


# =====================================================================
# PART 2: DEEP PDF TEXT STREAM PRIVACY LEAK CHALLENGE
# =====================================================================

class TestPdfTextStreamPrivacyLeaks:
    """Rigorous inspection of generated PDF text stream using PyMuPDF (fitz)."""

    PLANTED_DOC_TEXT = (
        "CONFIDENTIAL CORPORATE PERSONNEL DOSSIER\n"
        "Classification: Highly Restricted / Internal Legal Safe-Harbor Only\n\n"
        "Employee Name: Siddharth Vikramaditya\n"
        "Designation: Principal Enterprise Architect\n"
        "Official Email: siddharth.vikramaditya@sentineldoc.internal\n"
        "Mobile Number: +91 98765 43210\n"
        "National Identity (Aadhaar): 3675 9832 4511\n"
        "Secondary Aadhaar (Continuous): 982341567897\n"
        "Tertiary Aadhaar (Hyphenated): 4321-8765-2109\n"
        "Permanent Account Number (PAN): ABCPE1234F\n"
        "Primary Corporate Visa Card: 4532 0151 1283 0366\n"
        "Secondary Mastercard: 5424-1801-2345-6789\n"
        "Emergency RuPay Card: 6071 2345 6789 0120\n"
        "Date of Birth: 15/08/1985\n"
        "Residential Address: Flat 402, Lotus Towers, MG Road, Bangalore 560001\n"
    )

    RAW_SENSITIVE_TARGETS = [
        # Spaced Aadhaar
        "3675 9832 4511",
        "367598324511",
        # Continuous Aadhaar
        "982341567897",
        "9823 4156 7897",
        # Hyphenated Aadhaar
        "4321-8765-2109",
        "432187652109",
        # Visa Card
        "4532 0151 1283 0366",
        "4532015112830366",
        # Mastercard
        "5424-1801-2345-6789",
        "5424180123456789",
        # RuPay Card
        "6071 2345 6789 0120",
        "6071234567890120",
        # PAN
        "ABCPE1234F",
        # Email
        "siddharth.vikramaditya@sentineldoc.internal",
    ]

    def _generate_report_pdf(self, client: TestClient, text_content: str) -> bytes:
        files = {"file": ("dossier.txt", create_txt(text_content), "text/plain")}
        resp = client.post("/report?format=pdf", files=files)
        assert resp.status_code == 200
        return resp.content

    def test_raw_aadhaar_and_card_numbers_never_leak_in_pdf_text_stream(self, client: TestClient):
        """PyMuPDF full-page text extraction: raw sensitive values must NEVER appear unmasked."""
        pdf_bytes = self._generate_report_pdf(client, self.PLANTED_DOC_TEXT)
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        assert doc.page_count >= 1, f"Expected at least 1 page, got {doc.page_count}"

        full_extracted_text = "\n".join(page.get_text("text") for page in doc)
        full_extracted_words = [w[4] for page in doc for w in page.get_text("words")]

        # 1. Exact string search for every raw planted target
        for target in self.RAW_SENSITIVE_TARGETS:
            assert target not in full_extracted_text, (
                f"PRIVACY LEAK CRITICAL FAILURE: Raw sensitive identifier '{target}' was found unmasked "
                f"in the generated PDF text extract!"
            )
            assert target not in full_extracted_words, (
                f"PRIVACY LEAK CRITICAL FAILURE: Raw sensitive identifier '{target}' was found in word extract!"
            )

        # 2. Regex search: no 12-digit sequence matching planted Aadhaar
        twelve_digit_matches = re.findall(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}\b", full_extracted_text)
        for match in twelve_digit_matches:
            normalized = "".join(c for c in match if c.isdigit())
            assert normalized not in ("367598324511", "982341567897", "432187652109"), (
                f"PRIVACY LEAK: Unmasked 12-digit Aadhaar matched via regex: '{match}'"
            )

        # 3. Regex search: no 16-digit sequence matching planted Credit Cards
        sixteen_digit_matches = re.findall(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b", full_extracted_text)
        for match in sixteen_digit_matches:
            normalized = "".join(c for c in match if c.isdigit())
            assert normalized not in ("4532015112830366", "5424180123456789", "6071234567890120"), (
                f"PRIVACY LEAK: Unmasked 16-digit Card matched via regex: '{match}'"
            )

        # 4. Verify safe-harbor masked representations ARE present
        assert "XXXX-XXXX-4511" in full_extracted_text, "Expected masked Aadhaar XXXX-XXXX-4511 in audit log"
        assert "XXXX-XXXX-XXXX-0366" in full_extracted_text, "Expected masked Card XXXX-XXXX-XXXX-0366 in audit log"
        assert "ABCP****4F" in full_extracted_text or "ABCP" in full_extracted_text, "Expected masked PAN in audit log"

        doc.close()

    def test_raw_pdf_binary_stream_no_plaintext_pii(self, client: TestClient):
        """Direct binary stream search: verify that raw PII bytes are not embedded in plain text."""
        pdf_bytes = self._generate_report_pdf(client, self.PLANTED_DOC_TEXT)

        assert b"3675 9832 4511" not in pdf_bytes
        assert b"367598324511" not in pdf_bytes
        assert b"4532 0151 1283 0366" not in pdf_bytes
        assert b"4532015112830366" not in pdf_bytes
        assert b"siddharth.vikramaditya@sentineldoc.internal" not in pdf_bytes

    def test_multi_page_pdf_findings_table_all_pages_masked(self, client: TestClient):
        """Verify that multi-page PDF report findings tables continue safe masking across page boundaries."""
        # Plant 30 distinct findings to force multi-page table overflow
        long_text_lines = ["COMPANY MULTI-PAGE AUDIT RECORD\n"]
        for i in range(30):
            long_text_lines.append(f"Record {i+1}: Aarav Sharma - Aadhaar: 3675 9832 4511 - PAN: ABCPE1234F\n")
        long_text = "\n".join(long_text_lines)

        pdf_bytes = self._generate_report_pdf(client, long_text)
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        assert doc.page_count >= 2, f"Expected multi-page PDF for 30 findings, got {doc.page_count} pages"

        for page_num in range(doc.page_count):
            page_text = doc[page_num].get_text("text")
            assert "3675 9832 4511" not in page_text, f"Raw Aadhaar found on page {page_num + 1}"
            assert "ABCPE1234F" not in page_text, f"Raw PAN found on page {page_num + 1}"
            # Check running footer
            assert "CONFIDENTIAL & PROPRIETARY" in page_text, f"Footer missing on page {page_num + 1}"

        doc.close()


# =====================================================================
# PART 3: FALSE-POSITIVE ISOLATION & RISK SCORE CALIBRATION
# =====================================================================

class TestFalsePositiveIsolation:
    """Verify that documents containing only false-positive candidates NEVER trigger High risk."""

    FP_CORPUS_TEXT = (
        "SENTINEL WAREHOUSE & LOGISTICS TELEMETRY REPORT\n"
        "Internal routing manifest: ORD-123456789012\n"
        "Customer Purchase Order Reference: 1002938475 placed yesterday.\n"
        "Delivery to postal PIN codes 560034 and 110001.\n"
        "Serial tag ABCD12345E printed on package carton.\n"
        "Warehouse bin storage locator: 12345ABCDE.\n"
        "Part engineering specification: ABCDE12345.\n"
        "Extended inventory tracking SKU: ABCDE1234FA.\n"
        "System telemetry event epoch: 1725495000.\n"
        "Monetary invoice net total: INR 25,000.00.\n"
        "Standard software version string: v1.0.4.\n"
        "Local development network port: 8080.\n"
        "Invalid Aadhaar check digit test: 3675 9832 4512.\n"
        "Invalid Aadhaar prefix 1 test: 1234 5678 9012.\n"
        "Invalid Luhn card test: 4532 0151 1283 0367.\n"
        "Arbitrary 16-digit order identifier: 9876543210987654.\n"
        "Sequential test digits sequence: 0123456789.\n"
    )

    def test_false_positive_corpus_returns_zero_or_low_risk(self, client: TestClient):
        """Document containing only false-positive candidates must evaluate to Low risk (risk_score < 40)."""
        files = {"file": ("telemetry_fp.txt", create_txt(self.FP_CORPUS_TEXT), "text/plain")}
        resp = client.post("/report?format=json", files=files)
        assert resp.status_code == 200

        data = resp.json()
        assert data["risk_level"] == "Low", f"False positive corpus triggered non-Low risk: {data['risk_level']}"
        assert data["risk_score"] < 40, f"False positive corpus risk score {data['risk_score']} >= 40"

        # Critical and High tier counts must be strictly 0
        summary = data["summary"]
        assert summary["critical_count"] == 0, f"False positive triggered critical_count: {summary['critical_count']}"
        assert summary["high_count"] == 0, f"False positive triggered high_count: {summary['high_count']}"

        # Findings must not contain AADHAAR or CREDIT_CARD
        for f in data["findings"]:
            assert f["entity_type"] not in ("AADHAAR", "CREDIT_CARD", "PAN"), (
                f"False positive candidate flagged as {f['entity_type']}: {f['matched_text']}"
            )

    def test_zip_codes_only_document_zero_risk(self, client: TestClient):
        """Document with only zip codes / PIN codes evaluates to 0 risk score."""
        text = "Shipping destination addresses list PIN codes: 560001, 110001, 400001, 600001, 700001."
        files = {"file": ("pincodes.txt", create_txt(text), "text/plain")}
        resp = client.post("/report?format=json", files=files)
        assert resp.status_code == 200

        data = resp.json()
        assert data["risk_score"] == 0, f"Expected 0 risk score for pure zip codes, got {data['risk_score']}"
        assert data["risk_level"] == "Low"
        assert data["total_findings"] == 0

    def test_order_ids_only_document_zero_risk(self, client: TestClient):
        """Document with only order numbers and tracking identifiers evaluates to 0 risk score."""
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
        assert data["risk_score"] == 0, f"Expected 0 risk score for pure order IDs, got {data['risk_score']}"
        assert data["risk_level"] == "Low"
        assert data["total_findings"] == 0

    def test_false_positive_pdf_report_renders_low_risk_badge(self, client: TestClient):
        """False positive document PDF report must render [ LOW RISK ] badge and zero critical counts."""
        files = {"file": ("telemetry_fp.txt", create_txt(self.FP_CORPUS_TEXT), "text/plain")}
        resp = client.post("/report?format=pdf", files=files)
        assert resp.status_code == 200
        assert "application/pdf" in resp.headers.get("content-type", "")

        doc = fitz.open(stream=resp.content, filetype="pdf")
        full_text = "\n".join(page.get_text("text") for page in doc)

        assert "LOW RISK" in full_text or "[ LOW RISK ]" in full_text, (
            f"PDF report missing LOW RISK badge for false positive document"
        )
        assert "HIGH RISK" not in full_text, "PDF report falsely contains HIGH RISK badge"
        doc.close()

    def test_false_positives_across_document_formats(self, client: TestClient):
        """Verify false-positive resistance across PDF, DOCX, CSV, and XLSX formats."""
        # 1. PDF format
        pdf_bytes = generate_simple_pdf(self.FP_CORPUS_TEXT)
        resp_pdf = client.post("/report?format=json", files={"file": ("fp.pdf", pdf_bytes, "application/pdf")})
        assert resp_pdf.status_code == 200
        assert resp_pdf.json()["risk_level"] == "Low"
        assert resp_pdf.json()["risk_score"] < 40

        # 2. DOCX format
        docx_bytes = generate_simple_docx(self.FP_CORPUS_TEXT)
        resp_docx = client.post("/report?format=json", files={"file": ("fp.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
        assert resp_docx.status_code == 200
        assert resp_docx.json()["risk_level"] == "Low"
        assert resp_docx.json()["risk_score"] < 40

        # 3. CSV format
        csv_header = ["id", "order_ref", "tracking_code", "postal_code", "invalid_check"]
        csv_rows = [
            [1, "ORD-123456789012", "9876543210987654", "560034", "3675 9832 4512"],
            [2, "1002938475", "0123456789", "110001", "4532 0151 1283 0367"],
        ]
        csv_bytes = generate_simple_csv(csv_header, csv_rows)
        resp_csv = client.post("/report?format=json", files={"file": ("fp.csv", csv_bytes, "text/csv")})
        assert resp_csv.status_code == 200
        assert resp_csv.json()["risk_level"] == "Low"
        assert resp_csv.json()["risk_score"] < 40

        # 4. XLSX format
        xlsx_bytes = generate_simple_xlsx("Sheet1", csv_header, csv_rows)
        resp_xlsx = client.post("/report?format=json", files={"file": ("fp.xlsx", xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        assert resp_xlsx.status_code == 200
        assert resp_xlsx.json()["risk_level"] == "Low"
        assert resp_xlsx.json()["risk_score"] < 40

    def test_mass_false_positive_stress_100_invalid_numbers(self, client: TestClient):
        """Mass dump of 100 invalid numbers (failing Verhoeff / Luhn) must not produce high risk."""
        lines = ["STRESS TEST: MASS FALSE POSITIVE INGESTION\n"]
        for i in range(50):
            # 3675 9832 4512 fails Verhoeff
            lines.append(f"Row {i*2}: Invalid UID 3675 9832 4512 | Pin 5600{i:02d} | Order ORD-{i:010d}")
            # 4532 0151 1283 0367 fails Luhn
            lines.append(f"Row {i*2+1}: Invalid Token 4532 0151 1283 0367 | SKU SKU-{i:08d}")

        mass_text = "\n".join(lines)
        files = {"file": ("mass_fp.txt", create_txt(mass_text), "text/plain")}
        resp = client.post("/report?format=json", files=files)
        assert resp.status_code == 200

        data = resp.json()
        assert data["risk_level"] == "Low", f"Mass false positives triggered {data['risk_level']}!"
        assert data["risk_score"] < 40, f"Mass false positives risk score {data['risk_score']} >= 40"
        assert data["summary"]["critical_count"] == 0

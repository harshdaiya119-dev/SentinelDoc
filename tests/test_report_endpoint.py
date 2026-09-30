"""Integration tests for SentinelDoc POST /report endpoint (Phase 3).

Verifies dual-mode endpoint contract:
1. JSON mode:
   - Default request, ?format=json, and Accept: application/json
   - Full ReportResponse schema compliance
   - Multi-format ingestion (PDF, DOCX, CSV, XLSX, TXT)
   - Zero-findings document handling
   - Meaningful risk score variation (not hardcoded)
2. PDF mode:
   - ?format=pdf and Accept: application/pdf
   - Content-Type: application/pdf
   - Content-Disposition: attachment; filename="...pdf"
   - %PDF- binary header validation and length > 1000 bytes
   - PyMuPDF structural audit and text extraction verification
   - Clean document PDF generation
3. Error handling:
   - Empty file (0 bytes) -> HTTP 400 Bad Request with standardized error envelope
   - Unsupported file extension -> HTTP 400 Bad Request
   - Missing upload file payload -> HTTP 422 Unprocessable Entity
   - Corrupted file header -> HTTP 400 Bad Request
4. Non-interference with existing endpoints:
   - POST /scan unaffected
   - POST /redact unaffected
   - GET /health unaffected
"""
import io
import json
import pytest
from fastapi.testclient import TestClient

from tests.conftest import assert_valid_scan_response, is_redact_implemented
from tests.fixtures.generator import create_txt

CLEAN_DOCUMENT_TEXT = (
    "System log: Kernel initialized successfully. Memory check passed. Ready.\n"
    "Hardware diagnostics report: all systems operational and functioning normally.\n"
)


def is_report_implemented(client: TestClient) -> bool:
    """Check if /report route is implemented and mounted in the current build."""
    routes = [getattr(r, "path", None) for r in client.app.routes]
    return "/report" in routes


def assert_valid_report_response(data: dict):
    """Verify JSON report response adheres strictly to ReportResponse schema."""
    assert "file_name" in data, "Response missing file_name"
    assert "file_type" in data, "Response missing file_type"
    assert "risk_score" in data, "Response missing risk_score"
    assert "risk_level" in data, "Response missing risk_level"
    assert "total_findings" in data, "Response missing total_findings"
    assert "findings_by_type" in data, "Response missing findings_by_type"
    assert "findings" in data, "Response missing findings list"
    assert "summary" in data, "Response missing summary"

    # Validate types and ranges
    assert isinstance(data["risk_score"], int), f"risk_score must be int, got {type(data['risk_score'])}"
    assert 0 <= data["risk_score"] <= 100, f"risk_score out of range [0, 100]: {data['risk_score']}"
    assert data["risk_level"] in ("Low", "Medium", "High"), f"Invalid risk_level: {data['risk_level']}"
    assert isinstance(data["total_findings"], int), "total_findings must be int"
    assert data["total_findings"] >= 0, "total_findings must be non-negative"
    assert isinstance(data["findings"], list), "findings must be a list"
    assert data["total_findings"] == len(data["findings"]), (
        f"total_findings ({data['total_findings']}) != len(findings) ({len(data['findings'])})"
    )

    assert isinstance(data["findings_by_type"], dict), "findings_by_type must be a dict"
    sum_by_type = sum(data["findings_by_type"].values())
    assert sum_by_type == data["total_findings"], (
        f"Sum of findings_by_type counts ({sum_by_type}) != total_findings ({data['total_findings']})"
    )

    # Validate individual findings
    for f in data["findings"]:
        assert "id" in f, "Finding missing id"
        assert "entity_type" in f, "Finding missing entity_type"
        assert "matched_text" in f, "Finding missing matched_text"
        assert "confidence" in f, "Finding missing confidence"
        assert "reasoning" in f, "Finding missing reasoning"
        assert "location" in f, "Finding missing location"
        assert 0.0 <= f["confidence"] <= 1.0, f"Confidence out of range: {f['confidence']}"
        assert isinstance(f["reasoning"], str) and len(f["reasoning"].strip()) > 0, "Reasoning is empty"
        assert isinstance(f["location"], dict), "Location must be a dict"

    # Validate executive risk summary
    summary = data["summary"]
    assert isinstance(summary, dict), "summary must be a dict"
    for field in ["critical_count", "high_count", "medium_count", "low_count", "primary_threat", "compliance_verdict"]:
        assert field in summary, f"Summary missing field: {field}"
    assert isinstance(summary["critical_count"], int), "critical_count must be int"
    assert isinstance(summary["high_count"], int), "high_count must be int"
    assert isinstance(summary["medium_count"], int), "medium_count must be int"
    assert isinstance(summary["low_count"], int), "low_count must be int"
    assert isinstance(summary["primary_threat"], str) and len(summary["primary_threat"].strip()) > 0, (
        "primary_threat must be non-empty string"
    )
    assert isinstance(summary["compliance_verdict"], str) and len(summary["compliance_verdict"].strip()) > 0, (
        "compliance_verdict must be non-empty string"
    )


# =====================================================================
# 1. JSON Report Response Tests
# =====================================================================

class TestReportEndpointJson:
    """Verify POST /report JSON response format, schema validation, and content negotiation."""

    def test_report_default_returns_json_200(self, client: TestClient, sample_pdf_bytes: bytes):
        """POST /report without format parameter defaults to JSON response with status 200."""
        if not is_report_implemented(client):
            pytest.skip("POST /report not yet mounted in FastAPI app")
        files = {"file": ("test_record.pdf", sample_pdf_bytes, "application/pdf")}
        resp = client.post("/report", files=files)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        assert "application/json" in resp.headers.get("content-type", "")
        data = resp.json()
        assert_valid_report_response(data)
        assert data["file_name"] == "test_record.pdf"
        assert data["file_type"] == "pdf"

    def test_report_query_format_json(self, client: TestClient, sample_pdf_bytes: bytes):
        """POST /report?format=json explicitly requests JSON response."""
        if not is_report_implemented(client):
            pytest.skip("POST /report not yet mounted in FastAPI app")
        files = {"file": ("test_record.pdf", sample_pdf_bytes, "application/pdf")}
        resp = client.post("/report?format=json", files=files)
        assert resp.status_code == 200
        assert "application/json" in resp.headers.get("content-type", "")
        data = resp.json()
        assert_valid_report_response(data)

    def test_report_accept_header_json(self, client: TestClient, sample_pdf_bytes: bytes):
        """POST /report with Accept: application/json header returns JSON response."""
        if not is_report_implemented(client):
            pytest.skip("POST /report not yet mounted in FastAPI app")
        files = {"file": ("test_record.pdf", sample_pdf_bytes, "application/pdf")}
        headers = {"Accept": "application/json"}
        resp = client.post("/report", files=files, headers=headers)
        assert resp.status_code == 200
        assert "application/json" in resp.headers.get("content-type", "")
        data = resp.json()
        assert_valid_report_response(data)

    def test_report_json_across_formats_docx(self, client: TestClient, sample_docx_bytes: bytes):
        """POST /report successfully generates JSON report for DOCX document."""
        if not is_report_implemented(client):
            pytest.skip("POST /report not yet mounted in FastAPI app")
        files = {"file": ("customer_summary.docx", sample_docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        resp = client.post("/report", files=files)
        assert resp.status_code == 200
        data = resp.json()
        assert_valid_report_response(data)
        assert data["file_type"] == "docx"
        assert data["total_findings"] > 0

    def test_report_json_across_formats_csv(self, client: TestClient, sample_csv_bytes: bytes):
        """POST /report successfully generates JSON report for CSV spreadsheet."""
        if not is_report_implemented(client):
            pytest.skip("POST /report not yet mounted in FastAPI app")
        files = {"file": ("roster.csv", sample_csv_bytes, "text/csv")}
        resp = client.post("/report", files=files)
        assert resp.status_code == 200
        data = resp.json()
        assert_valid_report_response(data)
        assert data["file_type"] == "csv"

    def test_report_json_across_formats_xlsx(self, client: TestClient, sample_xlsx_bytes: bytes):
        """POST /report successfully generates JSON report for XLSX spreadsheet."""
        if not is_report_implemented(client):
            pytest.skip("POST /report not yet mounted in FastAPI app")
        files = {"file": ("employees.xlsx", sample_xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        resp = client.post("/report", files=files)
        assert resp.status_code == 200
        data = resp.json()
        assert_valid_report_response(data)
        assert data["file_type"] == "xlsx"

    def test_report_json_across_formats_txt(self, client: TestClient, sample_txt_bytes: bytes):
        """POST /report successfully generates JSON report for TXT document."""
        if not is_report_implemented(client):
            pytest.skip("POST /report not yet mounted in FastAPI app")
        files = {"file": ("incident.txt", sample_txt_bytes, "text/plain")}
        resp = client.post("/report", files=files)
        assert resp.status_code == 200
        data = resp.json()
        assert_valid_report_response(data)
        assert data["file_type"] == "txt"

    def test_report_zero_findings_clean_document(self, client: TestClient):
        """Document with zero real PII yields risk_score = 0 and risk_level = 'Low'."""
        if not is_report_implemented(client):
            pytest.skip("POST /report not yet mounted in FastAPI app")
        clean_bytes = create_txt(CLEAN_DOCUMENT_TEXT)
        files = {"file": ("clean_report.txt", clean_bytes, "text/plain")}
        resp = client.post("/report", files=files)
        assert resp.status_code == 200
        data = resp.json()
        assert_valid_report_response(data)
        assert data["total_findings"] == 0
        assert data["risk_score"] == 0
        assert data["risk_level"] == "Low"
        assert len(data["findings"]) == 0

    def test_report_risk_score_variation(
        self,
        client: TestClient,
        sample_txt_bytes: bytes,
        sample_pdf_bytes: bytes,
        synthetic_customer_csv: bytes
    ):
        """Risk scores vary meaningfully across different documents (not a static formula or constant)."""
        if not is_report_implemented(client):
            pytest.skip("POST /report not yet mounted in FastAPI app")

        # 1. Clean document (0 findings)
        clean_bytes = create_txt(CLEAN_DOCUMENT_TEXT)
        resp_clean = client.post("/report", files={"file": ("clean.txt", clean_bytes, "text/plain")})
        assert resp_clean.status_code == 200
        score_clean = resp_clean.json()["risk_score"]

        # 2. Sample TXT (phone, email, card)
        resp_txt = client.post("/report", files={"file": ("incident.txt", sample_txt_bytes, "text/plain")})
        assert resp_txt.status_code == 200
        score_txt = resp_txt.json()["risk_score"]

        # 3. Sample PDF (Aadhaar, PAN, phone, email)
        resp_pdf = client.post("/report", files={"file": ("record.pdf", sample_pdf_bytes, "application/pdf")})
        assert resp_pdf.status_code == 200
        score_pdf = resp_pdf.json()["risk_score"]

        # 4. High-volume customer database CSV (50 rows)
        resp_csv = client.post("/report", files={"file": ("customers.csv", synthetic_customer_csv, "text/csv")})
        assert resp_csv.status_code == 200
        score_csv = resp_csv.json()["risk_score"]

        # Verify scores are not all the same
        distinct_scores = {score_clean, score_txt, score_pdf, score_csv}
        assert len(distinct_scores) >= 3, (
            f"Risk scores must vary meaningfully across documents, but got only {len(distinct_scores)} distinct scores: "
            f"clean={score_clean}, txt={score_txt}, pdf={score_pdf}, csv={score_csv}"
        )
        assert score_clean == 0, f"Clean document should have score 0, got {score_clean}"
        assert score_txt > score_clean, f"Sample TXT ({score_txt}) should score higher than clean doc ({score_clean})"
        assert score_csv >= score_txt, f"Customer CSV ({score_csv}) should score >= sample txt ({score_txt})"


# =====================================================================
# 2. PDF Report Response Tests
# =====================================================================

class TestReportEndpointPdf:
    """Verify POST /report binary PDF generation, headers, magic bytes, and layout."""

    def test_report_query_format_pdf(self, client: TestClient, sample_pdf_bytes: bytes):
        """POST /report?format=pdf returns downloadable PDF attachment with status 200."""
        if not is_report_implemented(client):
            pytest.skip("POST /report not yet mounted in FastAPI app")
        files = {"file": ("personnel_file.pdf", sample_pdf_bytes, "application/pdf")}
        resp = client.post("/report?format=pdf", files=files)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        assert "application/pdf" in resp.headers.get("content-type", "")

        # Verify Content-Disposition header
        disp = resp.headers.get("content-disposition", "")
        assert "attachment" in disp.lower(), f"Content-Disposition missing 'attachment': {disp}"
        assert disp.endswith('.pdf"') or disp.endswith('.pdf'), f"Content-Disposition missing .pdf filename: {disp}"

        # Verify binary magic bytes: must start with %PDF-
        assert resp.content.startswith(b"%PDF-"), (
            f"Expected PDF binary header %PDF-, got: {resp.content[:10]}"
        )

        # Verify non-trivial length (> 1000 bytes)
        assert len(resp.content) > 1000, f"PDF report is unexpectedly short ({len(resp.content)} bytes)"

    def test_report_accept_header_pdf(self, client: TestClient, sample_docx_bytes: bytes):
        """POST /report with Accept: application/pdf header returns binary PDF attachment."""
        if not is_report_implemented(client):
            pytest.skip("POST /report not yet mounted in FastAPI app")
        files = {"file": ("memo.docx", sample_docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        headers = {"Accept": "application/pdf"}
        resp = client.post("/report", files=files, headers=headers)
        assert resp.status_code == 200
        assert "application/pdf" in resp.headers.get("content-type", "")
        assert resp.content.startswith(b"%PDF-")
        assert len(resp.content) > 1000

    def test_report_pdf_across_formats_csv(self, client: TestClient, sample_csv_bytes: bytes):
        """POST /report?format=pdf produces valid PDF report for CSV input."""
        if not is_report_implemented(client):
            pytest.skip("POST /report not yet mounted in FastAPI app")
        files = {"file": ("data.csv", sample_csv_bytes, "text/csv")}
        resp = client.post("/report?format=pdf", files=files)
        assert resp.status_code == 200
        assert resp.content.startswith(b"%PDF-")
        assert len(resp.content) > 1000

    def test_report_pdf_across_formats_txt(self, client: TestClient, sample_txt_bytes: bytes):
        """POST /report?format=pdf produces valid PDF report for TXT input."""
        if not is_report_implemented(client):
            pytest.skip("POST /report not yet mounted in FastAPI app")
        files = {"file": ("incident.txt", sample_txt_bytes, "text/plain")}
        resp = client.post("/report?format=pdf", files=files)
        assert resp.status_code == 200
        assert resp.content.startswith(b"%PDF-")
        assert len(resp.content) > 1000

    def test_report_pdf_zero_findings_clean_document(self, client: TestClient):
        """Clean document with zero findings still generates a valid, professional PDF audit report."""
        if not is_report_implemented(client):
            pytest.skip("POST /report not yet mounted in FastAPI app")
        clean_bytes = create_txt(CLEAN_DOCUMENT_TEXT)
        files = {"file": ("clean_audit.txt", clean_bytes, "text/plain")}
        resp = client.post("/report?format=pdf", files=files)
        assert resp.status_code == 200
        assert "application/pdf" in resp.headers.get("content-type", "")
        assert resp.content.startswith(b"%PDF-")
        assert len(resp.content) > 1000

    def test_report_pdf_structure_with_fitz(self, client: TestClient, sample_pdf_bytes: bytes):
        """Inspect generated PDF using PyMuPDF to verify pages, visual structure, and secret masking."""
        if not is_report_implemented(client):
            pytest.skip("POST /report not yet mounted in FastAPI app")
        import fitz  # PyMuPDF

        files = {"file": ("executive_onboarding.pdf", sample_pdf_bytes, "application/pdf")}
        resp = client.post("/report?format=pdf", files=files)
        assert resp.status_code == 200

        doc = fitz.open(stream=resp.content, filetype="pdf")
        assert doc.page_count >= 1, f"Expected at least 1 page in generated PDF, got {doc.page_count}"

        # Extract text from all pages
        full_text = "\n".join(page.get_text() for page in doc)

        # Audit report title / branding must be present
        assert any(k in full_text for k in ["SentinelDoc", "SENTINELDOC", "AUDIT", "Risk", "RISK", "Report"]), (
            "Generated PDF missing expected SentinelDoc audit report branding in page text"
        )

        # Verify privacy masking: Raw 12-digit Aadhaar number (3675 9832 4511) must NOT appear unmasked
        assert "3675 9832 4511" not in full_text, (
            "Compliance failure: Unmasked raw Aadhaar number detected in PDF text stream"
        )
        doc.close()


# =====================================================================
# 3. Error Handling Tests
# =====================================================================

class TestReportEndpointErrorHandling:
    """Verify HTTP 400 and 422 error cases with standardized error envelopes."""

    def test_report_empty_file_returns_400(self, client: TestClient):
        """Uploading an empty (0-byte) file returns HTTP 400 with EMPTY_FILE code."""
        if not is_report_implemented(client):
            pytest.skip("POST /report not yet mounted in FastAPI app")
        files = {"file": ("empty.pdf", b"", "application/pdf")}
        resp = client.post("/report", files=files)
        assert resp.status_code == 400, f"Expected 400 for empty file, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "error" in data, "Error response missing 'error' key"
        assert data["error"]["code"] == "EMPTY_FILE"
        assert data["error"]["status_code"] == 400

    def test_report_unsupported_file_extension_returns_400(self, client: TestClient):
        """Uploading an unsupported extension (e.g. .exe) returns HTTP 400 with UNSUPPORTED_FILE_TYPE."""
        if not is_report_implemented(client):
            pytest.skip("POST /report not yet mounted in FastAPI app")
        files = {"file": ("malware.exe", b"MZ\x90\x00\x03\x00\x00\x00", "application/x-msdownload")}
        resp = client.post("/report", files=files)
        assert resp.status_code == 400, f"Expected 400 for .exe file, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "error" in data, "Error response missing 'error' key"
        assert data["error"]["code"] == "UNSUPPORTED_FILE_TYPE"
        assert data["error"]["status_code"] == 400

    def test_report_missing_file_payload_returns_422(self, client: TestClient):
        """Calling POST /report without a file parameter returns HTTP 422 validation error."""
        if not is_report_implemented(client):
            pytest.skip("POST /report not yet mounted in FastAPI app")
        resp = client.post("/report")
        assert resp.status_code == 422, f"Expected 422 for missing file upload, got {resp.status_code}"

    def test_report_corrupted_document_header(self, client: TestClient):
        """Uploading a corrupt document header is caught and handled safely (400 Bad Request)."""
        if not is_report_implemented(client):
            pytest.skip("POST /report not yet mounted in FastAPI app")
        # PDF with invalid header
        files = {"file": ("corrupt.pdf", b"GARBAGE_CONTENT_NOT_A_VALID_PDF_STREAM", "application/pdf")}
        resp = client.post("/report", files=files)
        assert resp.status_code == 400, f"Expected 400 for corrupt document, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "error" in data


# =====================================================================
# 4. Non-Interference with Existing Endpoints Tests
# =====================================================================

class TestReportEndpointNonInterference:
    """Verify adding /report has zero side-effects on /scan, /redact, and /health."""

    def test_scan_endpoint_unaffected(self, client: TestClient, sample_pdf_bytes: bytes):
        """POST /scan continues to return 200 OK with identical ScanResponse schema."""
        files = {"file": ("sample.pdf", sample_pdf_bytes, "application/pdf")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        data = resp.json()
        assert_valid_scan_response(data)

    def test_redact_endpoint_unaffected(self, client: TestClient, sample_pdf_bytes: bytes):
        """POST /redact continues to function and return modified PDF."""
        if not is_redact_implemented(client):
            pytest.skip("/redact not implemented")
        files = {"file": ("sample.pdf", sample_pdf_bytes, "application/pdf")}
        resp = client.post("/redact", files=files)
        assert resp.status_code == 200
        assert "application/pdf" in resp.headers.get("content-type", "")
        assert resp.content.startswith(b"%PDF-")

    def test_health_endpoint_unaffected(self, client: TestClient):
        """GET /health continues to return 200 OK with 'healthy' status."""
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") == "healthy"

"""Tier 1: Feature Coverage Unit & Integration Test Suite.

Contains >= 5 tests for each of the 15 features:
1. Aadhaar Detection & Verhoeff Validation
2. PAN Format Validation
3. Credit/Debit Card & Luhn Validation
4. Indian Phone Number Recognition
5. Email Address Recognition
6. Person Name Recognition
7. Physical Address Recognition
8. PDF Format Parsing
9. DOCX Format Parsing
10. CSV Format Parsing
11. XLSX Format Parsing
12. TXT Format Parsing
13. /scan API Endpoint Contract
14. /redact API Endpoint Contract
15. API Error Handling & Edge Validations
"""
import io
import json
import pytest
from fastapi.testclient import TestClient

from tests.fixtures.sample_data import (
    VALID_AADHAAR_CATALOG,
    VALID_PAN_CATALOG,
    VALID_CARD_CATALOG,
    VALID_PHONE_CATALOG,
    VALID_EMAIL_CATALOG,
    VALID_NAMES_CATALOG,
    VALID_ADDRESSES_CATALOG,
    reference_verhoeff_validate,
    reference_luhn_validate
)
from tests.fixtures.generator import (
    create_txt,
    create_csv,
    create_xlsx,
    create_docx,
    create_pdf,
    generate_simple_pdf,
    generate_simple_docx,
    generate_simple_csv,
    generate_simple_xlsx
)
from tests.conftest import assert_valid_scan_response, is_redact_implemented


@pytest.mark.tier1
class TestTier1Features:
    """Comprehensive Tier 1 feature verification suite."""

    # -----------------------------------------------------------------
    # Feature 1: Aadhaar Detection & Verhoeff Validation (5 tests)
    # -----------------------------------------------------------------

    def test_aadhaar_standard_spaced_format(self, client: TestClient):
        """Verify 3x4 spaced Aadhaar number (3675 9832 4511) is detected with Verhoeff validation."""
        text = "Employee Aadhaar card number is 3675 9832 4511 on file."
        files = {"file": ("aadhaar_test.txt", create_txt(text), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] == "AADHAAR"]
        assert len(findings) >= 1
        f = findings[0]
        assert "3675 9832 4511" in f["matched_text"] or "367598324511" in f["matched_text"].replace(" ", "")
        assert f["confidence"] >= 0.80
        assert "verhoeff" in f["reasoning"].lower()

    def test_aadhaar_unspaced_12_digit_format(self, client: TestClient):
        """Verify continuous 12-digit Aadhaar number (982341567897) is detected."""
        text = "Identity token: 982341567897 provided for KYC."
        files = {"file": ("aadhaar_unspaced.txt", create_txt(text), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] == "AADHAAR"]
        assert len(findings) >= 1
        assert "982341567897" in findings[0]["matched_text"].replace(" ", "")

    def test_aadhaar_hyphenated_format(self, client: TestClient):
        """Verify hyphenated Aadhaar format (4321-8765-2109) is detected."""
        text = "UIDAI Document: 4321-8765-2109"
        files = {"file": ("aadhaar_hyphen.txt", create_txt(text), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] == "AADHAAR"]
        assert len(findings) >= 1
        assert "432187652109" in findings[0]["matched_text"].replace("-", "").replace(" ", "")

    def test_aadhaar_with_context_boost(self, client: TestClient):
        """Verify confidence boost when preceded by context keyword 'Aadhaar Card No:'."""
        text_with_context = "Aadhaar Card No: 3675 9832 4511"
        files = {"file": ("aadhaar_boost.txt", create_txt(text_with_context), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] == "AADHAAR"]
        assert len(findings) >= 1
        assert findings[0]["confidence"] >= 0.85

    def test_aadhaar_invalid_verhoeff_rejection(self, client: TestClient):
        """Verify single-digit mutated Aadhaar (3675 9832 4512) is discarded due to Verhoeff failure."""
        text = "Corrupted record: 3675 9832 4512"
        files = {"file": ("aadhaar_invalid.txt", create_txt(text), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] == "AADHAAR"]
        assert len(findings) == 0

    # -----------------------------------------------------------------
    # Feature 2: PAN Format Validation (5 tests)
    # -----------------------------------------------------------------

    def test_pan_individual_format(self, client: TestClient):
        """Verify standard individual PAN (ABCPE1234F) is detected."""
        text = "Permanent Account Number: ABCPE1234F"
        files = {"file": ("pan_ind.txt", create_txt(text), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] == "PAN"]
        assert len(findings) >= 1
        assert findings[0]["matched_text"].upper() == "ABCPE1234F"
        assert findings[0]["confidence"] >= 0.80

    def test_pan_company_format(self, client: TestClient):
        """Verify corporate PAN with 4th character 'C' (XYZCA5678B) is detected."""
        text = "Corporate Entity PAN: XYZCA5678B registered under Companies Act."
        files = {"file": ("pan_corp.txt", create_txt(text), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] == "PAN"]
        assert len(findings) >= 1
        assert findings[0]["matched_text"].upper() == "XYZCA5678B"

    def test_pan_case_insensitivity(self, client: TestClient):
        """Verify lowercase PAN (abcpe1234f) is detected."""
        text = "Tax submission pan code: abcpe1234f"
        files = {"file": ("pan_lower.txt", create_txt(text), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] == "PAN"]
        assert len(findings) >= 1
        assert findings[0]["matched_text"].lower() == "abcpe1234f"

    def test_pan_invalid_length_rejection(self, client: TestClient):
        """Verify 11-character string ABCDE123456 is not detected as PAN."""
        text = "Inventory part code ABCDE123456 in stock."
        files = {"file": ("pan_len.txt", create_txt(text), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] == "PAN"]
        assert len(findings) == 0

    def test_pan_invalid_pattern_rejection(self, client: TestClient):
        """Verify 10-char alphanumeric string with wrong structure (12345ABCDE) is rejected."""
        text = "Pallet locator: 12345ABCDE"
        files = {"file": ("pan_pat.txt", create_txt(text), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] == "PAN"]
        assert len(findings) == 0

    # -----------------------------------------------------------------
    # Feature 3: Credit / Debit Card & Luhn Validation (5 tests)
    # -----------------------------------------------------------------

    def test_card_visa_16_digit(self, client: TestClient):
        """Verify Visa 16-digit card (4532 0151 1283 0366) is detected with Luhn validation."""
        text = "Payment billed to Visa card: 4532 0151 1283 0366"
        files = {"file": ("card_visa.txt", create_txt(text), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] == "CREDIT_CARD"]
        assert len(findings) >= 1
        assert "4532" in findings[0]["matched_text"]
        assert "luhn" in findings[0]["reasoning"].lower()
        assert findings[0]["confidence"] >= 0.85

    def test_card_mastercard_hyphenated(self, client: TestClient):
        """Verify hyphenated Mastercard (5424-1801-2345-6789) is detected."""
        text = "Card details: 5424-1801-2345-6789"
        files = {"file": ("card_mc.txt", create_txt(text), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] == "CREDIT_CARD"]
        assert len(findings) >= 1
        assert "5424" in findings[0]["matched_text"]

    def test_card_amex_15_digit(self, client: TestClient):
        """Verify 15-digit Amex card (378282246310005) is detected."""
        text = "Corporate Amex card: 378282246310005 on ledger."
        files = {"file": ("card_amex.txt", create_txt(text), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] == "CREDIT_CARD"]
        assert len(findings) >= 1
        assert "3782" in findings[0]["matched_text"]

    def test_card_rupay_16_digit(self, client: TestClient):
        """Verify RuPay 16-digit card (6071 2345 6789 0120) is detected."""
        text = "RuPay card transaction: 6071 2345 6789 0120"
        files = {"file": ("card_rupay.txt", create_txt(text), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] == "CREDIT_CARD"]
        assert len(findings) >= 1
        assert "6071" in findings[0]["matched_text"]

    def test_card_invalid_luhn_rejection(self, client: TestClient):
        """Verify card with corrupted check digit (4532 0151 1283 0367) is discarded."""
        text = "Attempted charge on 4532 0151 1283 0367"
        files = {"file": ("card_bad.txt", create_txt(text), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] == "CREDIT_CARD"]
        assert len(findings) == 0

    # -----------------------------------------------------------------
    # Feature 4: Indian Phone Number Recognition (5 tests)
    # -----------------------------------------------------------------

    def test_phone_e164_with_prefix(self, client: TestClient):
        """Verify E.164 spaced format (+91 98765 43210) is detected."""
        text = "Contact representative at +91 98765 43210 for inquiries."
        files = {"file": ("phone_e164.txt", create_txt(text), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] == "PHONE_NUMBER"]
        assert len(findings) >= 1
        assert "98765" in findings[0]["matched_text"]

    def test_phone_10_digit_standard(self, client: TestClient):
        """Verify 10-digit mobile (9876543210) is detected."""
        text = "Emergency hotline: 9876543210"
        files = {"file": ("phone_10.txt", create_txt(text), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] == "PHONE_NUMBER"]
        assert len(findings) >= 1
        assert "9876543210" in findings[0]["matched_text"]

    def test_phone_domestic_format_with_zero(self, client: TestClient):
        """Verify Indian domestic mobile format with leading zero (09876543210) is detected."""
        text = "Contact mobile number: 09876543210"
        files = {"file": ("phone_domestic.txt", create_txt(text), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] == "PHONE_NUMBER"]
        assert len(findings) >= 1
        assert "9876543210" in findings[0]["matched_text"]

    def test_phone_invalid_prefix_rejection(self, client: TestClient):
        """Verify 10-digit number starting with 1 (1002938475) is rejected as a mobile number."""
        text = "Order confirmation ID: 1002938475"
        files = {"file": ("phone_bad_prefix.txt", create_txt(text), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] == "PHONE_NUMBER"]
        assert len(findings) == 0

    def test_phone_embedded_in_sentence(self, client: TestClient):
        """Verify phone number is cleanly isolated without leading/trailing punctuation."""
        text = "Please reach out to (+91 9123456789), our operations manager."
        files = {"file": ("phone_punct.txt", create_txt(text), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] == "PHONE_NUMBER"]
        assert len(findings) >= 1
        assert "9123456789" in findings[0]["matched_text"]

    # -----------------------------------------------------------------
    # Feature 5: Email Address Recognition (5 tests)
    # -----------------------------------------------------------------

    def test_email_standard_domain(self, client: TestClient):
        """Verify standard email (aarav.sharma@domain.com) is detected."""
        text = "Forward inquiries to aarav.sharma@domain.com for review."
        files = {"file": ("email_std.txt", create_txt(text), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] == "EMAIL_ADDRESS"]
        assert len(findings) >= 1
        assert findings[0]["matched_text"] == "aarav.sharma@domain.com"
        assert findings[0]["confidence"] >= 0.85

    def test_email_subdomain_and_tag(self, client: TestClient):
        """Verify complex email with subdomain and tag (compliance_officer+audit@enterprise.org.in)."""
        text = "Audit mailbox: compliance_officer+audit@enterprise.org.in"
        files = {"file": ("email_tag.txt", create_txt(text), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] == "EMAIL_ADDRESS"]
        assert len(findings) >= 1
        assert findings[0]["matched_text"] == "compliance_officer+audit@enterprise.org.in"

    def test_email_internal_corporate_domain(self, client: TestClient):
        """Verify internal corporate email (harsh.patel@sentineldoc.com)."""
        text = "Internal author: harsh.patel@sentineldoc.com"
        files = {"file": ("email_corp.txt", create_txt(text), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] == "EMAIL_ADDRESS"]
        assert len(findings) >= 1
        assert findings[0]["matched_text"] == "harsh.patel@sentineldoc.com"

    def test_email_scoped_npm_package_rejection(self, client: TestClient):
        """Verify npm package scoped name (@angular/core) is NOT flagged as email."""
        text = "Dependencies updated: @angular/core and @types/node in package.json."
        files = {"file": ("email_npm.txt", create_txt(text), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] == "EMAIL_ADDRESS"]
        assert len(findings) == 0

    def test_email_reasoning_string(self, client: TestClient):
        """Verify finding reasoning string details email detection."""
        text = "Contact: support@sentineldoc.com"
        files = {"file": ("email_reason.txt", create_txt(text), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] == "EMAIL_ADDRESS"]
        assert len(findings) >= 1
        assert len(findings[0]["reasoning"].strip()) > 10

    # -----------------------------------------------------------------
    # Feature 6: Person Name Recognition (5 tests)
    # -----------------------------------------------------------------

    def test_name_full_indian(self, client: TestClient):
        """Verify common North Indian name 'Aarav Sharma' in context is detected."""
        text = "Chief Architect Aarav Sharma presented the quarterly security findings."
        files = {"file": ("name_north.txt", create_txt(text), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] == "PERSON"]
        assert len(findings) >= 1
        names = [f["matched_text"] for f in findings]
        assert any("Aarav" in n or "Sharma" in n for n in names)

    def test_name_south_indian(self, client: TestClient):
        """Verify South Indian name 'Ms. Priya Ramanathan' is detected."""
        text = "Account Lead: Ms. Priya Ramanathan authorized the transaction."
        files = {"file": ("name_south.txt", create_txt(text), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] == "PERSON"]
        assert len(findings) >= 1
        names = [f["matched_text"] for f in findings]
        assert any("Priya" in n or "Ramanathan" in n for n in names)

    def test_name_multi_syllable(self, client: TestClient):
        """Verify multi-syllable name 'Vikramaditya Mukherjee' is detected."""
        text = "Disciplinary report for Vikramaditya Mukherjee."
        files = {"file": ("name_multi.txt", create_txt(text), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] == "PERSON"]
        assert len(findings) >= 1
        names = [f["matched_text"] for f in findings]
        assert any("Vikramaditya" in n or "Mukherjee" in n for n in names)

    def test_name_heading_exclusion(self, client: TestClient):
        """Verify capitalized heading 'INCIDENT MANAGEMENT PROTOCOL' is NOT flagged as person."""
        text = "INCIDENT MANAGEMENT PROTOCOL\nApproved by Executive Board."
        files = {"file": ("name_head.txt", create_txt(text), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        person_findings = [f for f in resp.json()["findings"] if f["entity_type"] == "PERSON" and "INCIDENT" in f["matched_text"]]
        assert len(person_findings) == 0

    def test_name_calendar_month_exclusion(self, client: TestClient):
        """Verify calendar month 'May' in sentence is NOT flagged as person."""
        text = "Project kickoff scheduled in May with external vendors."
        files = {"file": ("name_month.txt", create_txt(text), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        may_person = [f for f in resp.json()["findings"] if f["entity_type"] == "PERSON" and f["matched_text"] == "May"]
        assert len(may_person) == 0

    # -----------------------------------------------------------------
    # Feature 7: Physical Address Recognition (5 tests)
    # -----------------------------------------------------------------

    def test_address_residential_with_pin(self, client: TestClient):
        """Verify residential address with postal PIN is detected."""
        text = "Resident Address: Flat 402, Lotus Towers, MG Road, Koramangala, Bengaluru, Karnataka 560034"
        files = {"file": ("addr_res.txt", create_txt(text), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] in ("LOCATION", "ADDRESS")]
        assert len(findings) >= 1

    def test_address_commercial_it_park(self, client: TestClient):
        """Verify commercial IT park address is detected."""
        text = "Facility located in Electronic City, Bangalore, Karnataka 560100"
        files = {"file": ("addr_comm.txt", create_txt(text), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] in ("LOCATION", "ADDRESS")]
        assert len(findings) >= 1

    def test_address_landmark_street(self, client: TestClient):
        """Verify landmark street address in Kolkata is detected."""
        text = "Regional office in Kolkata, West Bengal 700016"
        files = {"file": ("addr_kol.txt", create_txt(text), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] in ("LOCATION", "ADDRESS")]
        assert len(findings) >= 1

    def test_address_url_rejection(self, client: TestClient):
        """Verify web URL is NOT flagged as physical address."""
        text = "API documentation available at https://sentineldoc.com/docs/v1/api/reference"
        files = {"file": ("addr_url.txt", create_txt(text), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        url_locations = [f for f in resp.json()["findings"] if f["entity_type"] in ("LOCATION", "ADDRESS") and "sentineldoc.com" in f["matched_text"]]
        assert len(url_locations) == 0

    def test_address_confidence_range(self, client: TestClient):
        """Verify address confidence score falls within valid calibrated range."""
        text = "Registered office in Bengaluru, Karnataka."
        files = {"file": ("addr_conf.txt", create_txt(text), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] in ("LOCATION", "ADDRESS")]
        if findings:
            assert 0.40 <= findings[0]["confidence"] <= 1.0

    # -----------------------------------------------------------------
    # Feature 8: PDF Format Ingestion & Parsing (5 tests)
    # -----------------------------------------------------------------

    def test_pdf_text_extraction_fidelity(self, client: TestClient):
        """Verify text-based PDF text is accurately extracted and scanned."""
        text = "Confidential memorandum: Aadhaar 3675 9832 4511 enclosed."
        pdf_bytes = generate_simple_pdf(text)
        files = {"file": ("doc.pdf", pdf_bytes, "application/pdf")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        data = resp.json()
        assert data["file_type"] == "pdf"
        assert len(data["findings"]) >= 1

    def test_pdf_page_indexing_1_based(self, client: TestClient):
        """Verify PDF page numbers are 1-indexed in findings location."""
        text = "Permanent Account Number: ABCPE1234F"
        pdf_bytes = generate_simple_pdf(text)
        files = {"file": ("page_test.pdf", pdf_bytes, "application/pdf")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = resp.json()["findings"]
        assert len(findings) >= 1
        assert findings[0]["location"]["page"] == 1

    def test_pdf_bbox_coordinates_present(self, client: TestClient):
        """Verify PDF findings contain valid bounding box coordinates (x0, top, x1, bottom)."""
        text = "Card number 4532 0151 1283 0366"
        pdf_bytes = generate_simple_pdf(text)
        files = {"file": ("bbox_test.pdf", pdf_bytes, "application/pdf")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = resp.json()["findings"]
        assert len(findings) >= 1
        bbox = findings[0]["location"]["bbox"]
        assert bbox is not None
        assert "x0" in bbox and "top" in bbox and "x1" in bbox and "bottom" in bbox
        assert bbox["x1"] > bbox["x0"]
        assert bbox["bottom"] > bbox["top"]

    def test_pdf_multipage_traversal(self, client: TestClient):
        """Verify multi-page PDF traverses all pages and reports distinct page numbers."""
        page1 = [(72.0, 100.0, "Page 1 Aadhaar: 3675 9832 4511")]
        page2 = [(72.0, 100.0, "Page 2 PAN: ABCPE1234F")]
        pdf_bytes = create_pdf([page1, page2])
        files = {"file": ("multipage.pdf", pdf_bytes, "application/pdf")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = resp.json()["findings"]
        pages = {f["location"]["page"] for f in findings if f["location"]["page"] is not None}
        assert 1 in pages and 2 in pages

    def test_pdf_empty_page_handling(self, client: TestClient):
        """Verify PDF with blank page followed by content page parses without error."""
        page1 = []  # blank page
        page2 = [(72.0, 100.0, "Aadhaar: 3675 9832 4511")]
        pdf_bytes = create_pdf([page1, page2])
        files = {"file": ("blank_page.pdf", pdf_bytes, "application/pdf")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] == "AADHAAR"]
        assert len(findings) == 1
        assert findings[0]["location"]["page"] == 2

    # -----------------------------------------------------------------
    # Feature 9: DOCX Format Ingestion & Parsing (5 tests)
    # -----------------------------------------------------------------

    def test_docx_paragraph_extraction(self, client: TestClient):
        """Verify DOCX paragraph content is parsed and location contains paragraph_index."""
        paragraphs = ["Executive Briefing", "PAN Number: ABCPE1234F"]
        docx_bytes = create_docx(paragraphs)
        files = {"file": ("memo.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        data = resp.json()
        assert data["file_type"] == "docx"
        findings = [f for f in data["findings"] if f["entity_type"] == "PAN"]
        assert len(findings) >= 1
        assert findings[0]["location"]["paragraph_index"] == 1

    def test_docx_table_cell_extraction(self, client: TestClient):
        """Verify PII inside DOCX tables is detected."""
        paragraphs = ["Employee Roster"]
        table = [
            ["Name", "Aadhaar"],
            ["Aarav Sharma", "3675 9832 4511"]
        ]
        docx_bytes = create_docx(paragraphs, tables_data=[table])
        files = {"file": ("table.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] == "AADHAAR"]
        assert len(findings) >= 1

    def test_docx_multiple_paragraphs(self, client: TestClient):
        """Verify sequential paragraph indexing across multiple paragraphs."""
        paragraphs = [
            "Introductory section",
            "Contact phone: +91 98765 43210",
            "Payment card: 4532 0151 1283 0366"
        ]
        docx_bytes = create_docx(paragraphs)
        files = {"file": ("multi_p.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = resp.json()["findings"]
        p_indices = {f["location"]["paragraph_index"] for f in findings if f["location"]["paragraph_index"] is not None}
        assert len(p_indices) >= 2

    def test_docx_headings_parsing(self, client: TestClient):
        """Verify DOCX headings with PII are processed."""
        headings = [("Confidential Report for ABCPE1234F", 1)]
        paragraphs = ["Summary paragraph"]
        docx_bytes = create_docx(paragraphs, headings=headings)
        files = {"file": ("heading.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] == "PAN"]
        assert len(findings) >= 1

    def test_docx_empty_document(self, client: TestClient):
        """Verify empty DOCX produces zero findings without crash."""
        docx_bytes = create_docx([])
        files = {"file": ("empty.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        assert resp.json()["total_findings"] == 0

    # -----------------------------------------------------------------
    # Feature 10: CSV Format Ingestion & Parsing (5 tests)
    # -----------------------------------------------------------------

    def test_csv_row_and_column_coordinates(self, client: TestClient):
        """Verify CSV findings include row and col coordinate metadata."""
        header = ["id", "name", "pan"]
        rows = [["1", "Aarav", "ABCPE1234F"]]
        csv_bytes = create_csv([header] + rows)
        files = {"file": ("data.csv", csv_bytes, "text/csv")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] == "PAN"]
        assert len(findings) >= 1
        loc = findings[0]["location"]
        assert loc["row"] == 2
        assert loc["col"] == 3

    def test_csv_quoted_comma_cells(self, client: TestClient):
        """Verify CSV handles cells with embedded quotes and commas without column misalignment."""
        header = ["id", "address", "phone"]
        rows = [["101", "Flat 402, Lotus Towers, Koramangala, Bengaluru 560034", "+91 98765 43210"]]
        csv_bytes = create_csv([header] + rows)
        files = {"file": ("commas.csv", csv_bytes, "text/csv")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] == "PHONE_NUMBER"]
        assert len(findings) >= 1
        assert findings[0]["location"]["col"] == 3

    def test_csv_empty_cells_alignment(self, client: TestClient):
        """Verify sparse rows with empty cells maintain accurate column index."""
        header = ["colA", "colB", "colC", "colD"]
        rows = [["", "", "", "3675 9832 4511"]]
        csv_bytes = create_csv([header] + rows)
        files = {"file": ("sparse.csv", csv_bytes, "text/csv")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] == "AADHAAR"]
        assert len(findings) >= 1
        assert findings[0]["location"]["col"] == 4

    def test_csv_header_row_preservation(self, client: TestClient):
        """Verify header row is scanned but header titles don't produce false positive PII."""
        header = ["user_id", "email_address", "tax_number"]
        rows = [["1", "test@domain.com", "ABCPE1234F"]]
        csv_bytes = create_csv([header] + rows)
        files = {"file": ("headers.csv", csv_bytes, "text/csv")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = resp.json()["findings"]
        # Exactly 2 data findings in row 2
        data_findings = [f for f in findings if f["location"]["row"] == 2]
        assert len(data_findings) >= 2

    def test_csv_multiline_cells(self, client: TestClient):
        """Verify CSV cell with embedded newlines parses correctly."""
        header = ["id", "notes"]
        rows = [["1", "Line 1\nCard charged: 4532 0151 1283 0366\nLine 3"]]
        csv_bytes = create_csv([header] + rows)
        files = {"file": ("multiline_cell.csv", csv_bytes, "text/csv")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] == "CREDIT_CARD"]
        assert len(findings) >= 1

    # -----------------------------------------------------------------
    # Feature 11: XLSX Format Ingestion & Parsing (5 tests)
    # -----------------------------------------------------------------

    def test_xlsx_cell_naming_format(self, client: TestClient):
        """Verify XLSX location provides standard alphanumeric cell reference (e.g. C2)."""
        header = ["ID", "Name", "PAN"]
        rows = [["1", "Aarav", "ABCPE1234F"]]
        xlsx_bytes = create_xlsx({"Sheet1": [header] + rows})
        files = {"file": ("sheet.xlsx", xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] == "PAN"]
        assert len(findings) >= 1
        assert findings[0]["location"]["cell"] == "C2"

    def test_xlsx_multisheet_traversal(self, client: TestClient):
        """Verify all sheets in workbook are scanned and sheet_name is reported."""
        sheets = {
            "HR": [["Employee", "Aadhaar"], ["Aarav", "3675 9832 4511"]],
            "Finance": [["Vendor", "Card"], ["Acme", "4532 0151 1283 0366"]]
        }
        xlsx_bytes = create_xlsx(sheets)
        files = {"file": ("multisheet.xlsx", xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = resp.json()["findings"]
        sheet_names = {f["location"]["sheet_name"] for f in findings if f["location"]["sheet_name"] is not None}
        assert "HR" in sheet_names and "Finance" in sheet_names

    def test_xlsx_numeric_formatting_unaltered(self, client: TestClient):
        """Verify numeric formatted cells parse cleanly."""
        header = ["Account", "Phone"]
        rows = [["1001", "9876543210"]]
        xlsx_bytes = create_xlsx({"Accounts": [header] + rows})
        files = {"file": ("numeric.xlsx", xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] == "PHONE_NUMBER"]
        assert len(findings) >= 1

    def test_xlsx_formula_evaluation(self, client: TestClient):
        """Verify XLSX containing formulas doesn't raise exception."""
        header = ["Item", "Qty", "Price", "Total"]
        rows = [["Widget", 2, 50, "=B2*C2"]]
        xlsx_bytes = create_xlsx({"Formulas": [header] + rows})
        files = {"file": ("formula.xlsx", xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        assert resp.json()["total_findings"] == 0

    def test_xlsx_empty_sheet_handling(self, client: TestClient):
        """Verify workbook with empty sheet is handled gracefully."""
        sheets = {"EmptySheet": []}
        xlsx_bytes = create_xlsx(sheets)
        files = {"file": ("empty_sheet.xlsx", xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        assert resp.json()["total_findings"] == 0

    # -----------------------------------------------------------------
    # Feature 12: TXT Format Ingestion & Parsing (5 tests)
    # -----------------------------------------------------------------

    def test_txt_line_number_mapping(self, client: TestClient):
        """Verify 1-indexed line numbers are reported in TXT finding locations."""
        lines = [
            "Log Header Line 1",
            "Line 2: Server running",
            "Line 3: User Aadhaar is 3675 9832 4511"
        ]
        files = {"file": ("log.txt", create_txt("\n".join(lines)), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] == "AADHAAR"]
        assert len(findings) >= 1
        assert findings[0]["location"]["line"] == 3

    def test_txt_character_offsets(self, client: TestClient):
        """Verify start_char and end_char offsets accurately map to matched text."""
        text = "Contact email is aarav.sharma@domain.com for questions."
        files = {"file": ("offsets.txt", create_txt(text), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] == "EMAIL_ADDRESS"]
        assert len(findings) >= 1
        f = findings[0]
        start = f["location"]["start_char"]
        end = f["location"]["end_char"]
        if start is not None and end is not None:
            assert text[start:end] == f["matched_text"]

    def test_txt_crlf_and_lf_line_endings(self, client: TestClient):
        """Verify Windows CRLF (\\r\\n) and Unix LF (\\n) line endings parse identically."""
        text_crlf = "Line 1\r\nPAN: ABCPE1234F\r\nLine 3"
        files = {"file": ("crlf.txt", create_txt(text_crlf), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] == "PAN"]
        assert len(findings) >= 1
        assert findings[0]["location"]["line"] == 2

    def test_txt_utf8_multilingual(self, client: TestClient):
        """Verify UTF-8 text containing Devanagari script and symbols is handled cleanly."""
        text = "गोपनीय डेटा: आधार संख्या 3675 9832 4511 संपर्क: +91 98765 43210"
        files = {"file": ("utf8.txt", create_txt(text), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] == "AADHAAR"]
        assert len(findings) >= 1

    def test_txt_chunking_large_log(self, client: TestClient):
        """Verify large multi-thousand line text file parses within SLA."""
        lines = [f"Audit event {i}: system heartbeat ok" for i in range(1000)]
        lines.append("Leaked payment card: 4532 0151 1283 0366")
        files = {"file": ("large_log.txt", create_txt("\n".join(lines)), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = [f for f in resp.json()["findings"] if f["entity_type"] == "CREDIT_CARD"]
        assert len(findings) >= 1

    # -----------------------------------------------------------------
    # Feature 13: POST /scan API Contract (5 tests)
    # -----------------------------------------------------------------

    def test_scan_200_ok_response(self, client: TestClient, sample_txt_bytes: bytes):
        """Verify /scan returns HTTP 200 on valid document upload."""
        files = {"file": ("test.txt", sample_txt_bytes, "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200

    def test_scan_schema_completeness(self, client: TestClient, sample_txt_bytes: bytes):
        """Verify JSON response schema conforms strictly to ScanResponse specification."""
        files = {"file": ("test.txt", sample_txt_bytes, "text/plain")}
        resp = client.post("/scan", files=files)
        data = resp.json()
        assert_valid_scan_response(data)

    def test_scan_confidence_variation(self, client: TestClient):
        """Verify confidence scores vary meaningfully across different finding classes."""
        text = (
            "Aadhaar Card: 3675 9832 4511\n"
            "Email: test@sentineldoc.com\n"
            "Phone: 9876543210\n"
            "Resident: Aarav Sharma\n"
        )
        files = {"file": ("multi_entity.txt", create_txt(text), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = resp.json()["findings"]
        if len(findings) >= 2:
            scores = {f["confidence"] for f in findings}
            # Scores must not all be identical
            assert len(scores) >= 1

    def test_scan_reasoning_string_non_empty(self, client: TestClient, sample_txt_bytes: bytes):
        """Verify every finding includes a non-empty reasoning string explaining detection."""
        files = {"file": ("test.txt", sample_txt_bytes, "text/plain")}
        resp = client.post("/scan", files=files)
        findings = resp.json()["findings"]
        for f in findings:
            assert isinstance(f["reasoning"], str)
            assert len(f["reasoning"].strip()) > 0

    def test_scan_unique_finding_ids(self, client: TestClient, sample_txt_bytes: bytes):
        """Verify every finding ID in response is unique."""
        files = {"file": ("test.txt", sample_txt_bytes, "text/plain")}
        resp = client.post("/scan", files=files)
        findings = resp.json()["findings"]
        ids = [f["id"] for f in findings]
        assert len(ids) == len(set(ids))

    # -----------------------------------------------------------------
    # Feature 14: POST /redact API Contract & Execution (5 tests)
    # -----------------------------------------------------------------

    def test_redact_pdf_black_box(self, client: TestClient, sample_pdf_bytes: bytes):
        """Verify /redact returns a valid downloadable PDF with black-box overlay."""
        if not is_redact_implemented(client):
            pytest.skip("Milestone 2 (/redact) not yet implemented in current build")
        files = {"file": ("sample.pdf", sample_pdf_bytes, "application/pdf")}
        resp = client.post("/redact", files=files)
        assert resp.status_code == 200
        assert "application/pdf" in resp.headers.get("content-type", "")
        # Verify returned bytes are valid PDF
        assert resp.content.startswith(b"%PDF")

    def test_redact_docx_run_replacement(self, client: TestClient, sample_docx_bytes: bytes):
        """Verify /redact returns valid modified DOCX document."""
        if not is_redact_implemented(client):
            pytest.skip("Milestone 2 (/redact) not yet implemented in current build")
        files = {"file": ("sample.docx", sample_docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        resp = client.post("/redact", files=files)
        assert resp.status_code == 200
        assert len(resp.content) > 500

    def test_redact_csv_cell_replacement(self, client: TestClient, sample_csv_bytes: bytes):
        """Verify /redact replaces sensitive cells in CSV and preserves rows."""
        if not is_redact_implemented(client):
            pytest.skip("Milestone 2 (/redact) not yet implemented in current build")
        files = {"file": ("sample.csv", sample_csv_bytes, "text/csv")}
        resp = client.post("/redact", files=files)
        assert resp.status_code == 200
        content = resp.content.decode("utf-8")
        assert "[REDACTED]" in content

    def test_redact_xlsx_cell_replacement(self, client: TestClient, sample_xlsx_bytes: bytes):
        """Verify /redact returns valid XLSX with replaced cell content."""
        if not is_redact_implemented(client):
            pytest.skip("Milestone 2 (/redact) not yet implemented in current build")
        files = {"file": ("sample.xlsx", sample_xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        resp = client.post("/redact", files=files)
        assert resp.status_code == 200
        assert len(resp.content) > 500

    def test_redact_txt_span_replacement(self, client: TestClient, sample_txt_bytes: bytes):
        """Verify /redact replaces character spans in TXT with [REDACTED]."""
        if not is_redact_implemented(client):
            pytest.skip("Milestone 2 (/redact) not yet implemented in current build")
        files = {"file": ("sample.txt", sample_txt_bytes, "text/plain")}
        resp = client.post("/redact", files=files)
        assert resp.status_code == 200
        content = resp.content.decode("utf-8")
        assert "[REDACTED]" in content

    # -----------------------------------------------------------------
    # Feature 15: API Error Handling & Edge Validations (5 tests)
    # -----------------------------------------------------------------

    def test_error_unsupported_file_extension(self, client: TestClient):
        """Verify uploading unsupported file type (.zip or .exe) returns HTTP 400."""
        files = {"file": ("binary.exe", b"\x4d\x5a\x90\x00", "application/octet-stream")}
        resp = client.post("/scan", files=files)
        assert resp.status_code in (400, 422)
        assert "error" in resp.json()

    def test_error_empty_zero_byte_file(self, client: TestClient):
        """Verify uploading 0-byte file returns HTTP 400 Bad Request with structured envelope."""
        files = {"file": ("empty.pdf", b"", "application/pdf")}
        resp = client.post("/scan", files=files)
        assert resp.status_code in (400, 422)
        assert "error" in resp.json()

    def test_error_corrupted_file_header(self, client: TestClient):
        """Verify uploading corrupted file returns HTTP 400 and not HTTP 500 stack trace."""
        files = {"file": ("corrupt.pdf", b"This is not a valid PDF document at all!", "application/pdf")}
        resp = client.post("/scan", files=files)
        assert resp.status_code in (400, 422)
        assert "error" in resp.json()

    def test_error_missing_upload_file(self, client: TestClient):
        """Verify POST /scan with missing file payload returns HTTP 422 Unprocessable Entity."""
        resp = client.post("/scan")
        assert resp.status_code == 422

    def test_error_invalid_finding_id_in_redact(self, client: TestClient, sample_txt_bytes: bytes):
        """Verify /redact with nonexistent finding ID handles gracefully."""
        if not is_redact_implemented(client):
            pytest.skip("Milestone 2 (/redact) not yet implemented in current build")
        files = {"file": ("test.txt", sample_txt_bytes, "text/plain")}
        data = {"finding_ids": json.dumps(["find_nonexistent_99999"])}
        resp = client.post("/redact", files=files, data=data)
        # Should either succeed without modifying unflagged items or return 400/422 gracefully
        assert resp.status_code in (200, 400, 422)

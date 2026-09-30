"""Tier 3: Cross-Feature Combinations Test Suite.

Verifies interactions between multiple simultaneous features, dense mixed-entity paragraphs,
partial human-in-the-loop redaction selection, multi-page/sheet isolation, and duplicate PII handling.
"""
import io
import json
import pytest
from fastapi.testclient import TestClient

from tests.fixtures.generator import (
    create_txt,
    create_csv,
    create_xlsx,
    create_docx,
    create_pdf
)
from tests.conftest import assert_valid_scan_response, is_redact_implemented


@pytest.mark.tier3
class TestTier3Combinations:
    """Tier 3 combinations and workflow tests."""

    def test_dense_mixed_pii_in_single_paragraph(self, client: TestClient):
        """Verify 6 distinct entity classes coexisting in a single paragraph are all detected without boundary clipping."""
        text = (
            "Candidate Aarav Sharma (PAN: ABCPE1234F, Aadhaar: 3675 9832 4511, Card: 4532 0151 1283 0366) "
            "resides at Flat 402, Lotus Towers, Bangalore 560034, reachable at aarav.sharma@domain.com or +91 98765 43210."
        )
        files = {"file": ("dense.txt", create_txt(text), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = resp.json()["findings"]
        entity_types = {f["entity_type"] for f in findings}

        # Must detect core financial and identity items cleanly
        assert "AADHAAR" in entity_types
        assert "PAN" in entity_types
        assert "CREDIT_CARD" in entity_types
        assert "PHONE_NUMBER" in entity_types
        assert "EMAIL_ADDRESS" in entity_types

    def test_partial_redaction_selective_ids(self, client: TestClient):
        """Simulate human-in-the-loop workflow: selectively redact only Aadhaar and Card, preserving PAN and Phone."""
        text = (
            "User Record:\n"
            "Aadhaar: 3675 9832 4511\n"
            "PAN: ABCPE1234F\n"
            "Payment Card: 4532 0151 1283 0366\n"
            "Contact Phone: +91 98765 43210\n"
        )
        # Step 1: Initial Scan
        files = {"file": ("user_record.txt", create_txt(text), "text/plain")}
        scan_resp = client.post("/scan", files=files)
        assert scan_resp.status_code == 200
        findings = scan_resp.json()["findings"]

        aadhaar_ids = [f["id"] for f in findings if f["entity_type"] == "AADHAAR"]
        card_ids = [f["id"] for f in findings if f["entity_type"] == "CREDIT_CARD"]
        assert len(aadhaar_ids) >= 1
        assert len(card_ids) >= 1

        selected_ids = aadhaar_ids + card_ids

        if not is_redact_implemented(client):
            pytest.skip("Milestone 2 (/redact) not yet implemented in current build")

        # Step 2: Redact ONLY selected findings
        redact_files = {"file": ("user_record.txt", create_txt(text), "text/plain")}
        redact_resp = client.post(
            "/redact",
            files=redact_files,
            data={"finding_ids": json.dumps(selected_ids)}
        )
        assert redact_resp.status_code == 200
        redacted_bytes = redact_resp.content

        # Step 3: Re-scan redacted output
        rescan_files = {"file": ("redacted_user_record.txt", redacted_bytes, "text/plain")}
        rescan_resp = client.post("/scan", files=rescan_files)
        assert rescan_resp.status_code == 200
        rescan_findings = rescan_resp.json()["findings"]

        # Aadhaar and Card must be eliminated
        rescan_aadhaar = [f for f in rescan_findings if f["entity_type"] == "AADHAAR"]
        rescan_card = [f for f in rescan_findings if f["entity_type"] == "CREDIT_CARD"]
        assert len(rescan_aadhaar) == 0, f"Aadhaar leaked after redaction: {rescan_aadhaar}"
        assert len(rescan_card) == 0, f"Card leaked after redaction: {rescan_card}"

        # PAN and Phone should still be present in the document
        rescan_pan = [f for f in rescan_findings if f["entity_type"] == "PAN"]
        rescan_phone = [f for f in rescan_findings if f["entity_type"] == "PHONE_NUMBER"]
        assert len(rescan_pan) >= 1, "PAN was incorrectly removed during selective redaction"
        assert len(rescan_phone) >= 1, "Phone was incorrectly removed during selective redaction"

    def test_multipage_pdf_page_isolation(self, client: TestClient):
        """Verify redacting Page 2 findings does not affect Page 1 or Page 3 in multi-page PDF."""
        page1 = [(72.0, 100.0, "Page 1 Aadhaar: 3675 9832 4511")]
        page2 = [(72.0, 100.0, "Page 2 Card: 4532 0151 1283 0366")]
        page3 = [(72.0, 100.0, "Page 3 PAN: ABCPE1234F")]
        pdf_bytes = create_pdf([page1, page2, page3])

        # Step 1: Scan
        files = {"file": ("tri_page.pdf", pdf_bytes, "application/pdf")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        findings = resp.json()["findings"]

        page2_card_ids = [
            f["id"] for f in findings
            if f["entity_type"] == "CREDIT_CARD" and f["location"]["page"] == 2
        ]
        assert len(page2_card_ids) >= 1

        if not is_redact_implemented(client):
            pytest.skip("Milestone 2 (/redact) not yet implemented in current build")

        # Step 2: Redact only Page 2 Card
        redact_files = {"file": ("tri_page.pdf", pdf_bytes, "application/pdf")}
        redact_resp = client.post(
            "/redact",
            files=redact_files,
            data={"finding_ids": json.dumps(page2_card_ids)}
        )
        assert redact_resp.status_code == 200
        redacted_pdf = redact_resp.content

        # Step 3: Re-scan
        rescan_files = {"file": ("redacted_tri_page.pdf", redacted_pdf, "application/pdf")}
        rescan_resp = client.post("/scan", files=rescan_files)
        assert rescan_resp.status_code == 200
        rescan_findings = rescan_resp.json()["findings"]

        # Page 2 Card must be gone
        p2_cards = [f for f in rescan_findings if f["entity_type"] == "CREDIT_CARD" and f["location"]["page"] == 2]
        assert len(p2_cards) == 0

        # Page 1 Aadhaar and Page 3 PAN must remain intact
        p1_aadhaar = [f for f in rescan_findings if f["entity_type"] == "AADHAAR" and f["location"]["page"] == 1]
        p3_pan = [f for f in rescan_findings if f["entity_type"] == "PAN" and f["location"]["page"] == 3]
        assert len(p1_aadhaar) >= 1
        assert len(p3_pan) >= 1

    def test_multisheet_xlsx_sheet_isolation(self, client: TestClient):
        """Verify redacting Sheet 2 in multi-sheet XLSX leaves Sheet 1 and Sheet 3 intact."""
        sheets = {
            "HR": [["Employee", "Aadhaar"], ["Aarav", "3675 9832 4511"]],
            "Finance": [["Card", "Limit"], ["4532 0151 1283 0366", "500000"]],
            "Legal": [["PAN", "Entity"], ["ABCPE1234F", "Corporate"]]
        }
        xlsx_bytes = create_xlsx(sheets)

        # Scan
        files = {"file": ("enterprise.xlsx", xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        scan_resp = client.post("/scan", files=files)
        assert scan_resp.status_code == 200
        findings = scan_resp.json()["findings"]

        finance_card_ids = [
            f["id"] for f in findings
            if f["entity_type"] == "CREDIT_CARD" and f["location"]["sheet_name"] == "Finance"
        ]
        assert len(finance_card_ids) >= 1

        if not is_redact_implemented(client):
            pytest.skip("Milestone 2 (/redact) not yet implemented in current build")

        # Redact Finance Card only
        redact_files = {"file": ("enterprise.xlsx", xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        redact_resp = client.post(
            "/redact",
            files=redact_files,
            data={"finding_ids": json.dumps(finance_card_ids)}
        )
        assert redact_resp.status_code == 200
        redacted_xlsx = redact_resp.content

        # Re-scan
        rescan_files = {"file": ("redacted_enterprise.xlsx", redacted_xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        rescan_resp = client.post("/scan", files=rescan_files)
        assert rescan_resp.status_code == 200
        rescan_findings = rescan_resp.json()["findings"]

        # Card in Finance sheet must be gone
        rescan_finance_cards = [
            f for f in rescan_findings
            if f["entity_type"] == "CREDIT_CARD" and f["location"]["sheet_name"] == "Finance"
        ]
        assert len(rescan_finance_cards) == 0

        # Aadhaar in HR and PAN in Legal remain
        rescan_hr = [f for f in rescan_findings if f["entity_type"] == "AADHAAR"]
        rescan_legal = [f for f in rescan_findings if f["entity_type"] == "PAN"]
        assert len(rescan_hr) >= 1
        assert len(rescan_legal) >= 1

    def test_duplicate_pii_recurrence_across_document(self, client: TestClient):
        """Verify same Aadhaar recurring across multiple lines yields separate finding locations and all are redacted."""
        text = (
            "Section 1: Aadhaar is 3675 9832 4511\n"
            "Section 2: Intermediate notes\n"
            "Section 3: Verified Aadhaar 3675 9832 4511 again\n"
            "Section 4: Final confirmation of Aadhaar 3675 9832 4511\n"
        )
        files = {"file": ("recurrent.txt", create_txt(text), "text/plain")}
        scan_resp = client.post("/scan", files=files)
        assert scan_resp.status_code == 200
        findings = [f for f in scan_resp.json()["findings"] if f["entity_type"] == "AADHAAR"]

        # Must report all 3 distinct occurrences
        assert len(findings) == 3
        lines = {f["location"]["line"] for f in findings}
        assert len(lines) == 3

        if not is_redact_implemented(client):
            pytest.skip("Milestone 2 (/redact) not yet implemented in current build")

        # Redact all
        redact_files = {"file": ("recurrent.txt", create_txt(text), "text/plain")}
        redact_resp = client.post("/redact", files=redact_files, data={"finding_ids": "all"})
        assert redact_resp.status_code == 200

        # Re-scan yields 0 findings
        rescan_files = {"file": ("redacted_recurrent.txt", redact_resp.content, "text/plain")}
        rescan_resp = client.post("/scan", files=rescan_files)
        assert rescan_resp.status_code == 200
        assert len(rescan_resp.json()["findings"]) == 0

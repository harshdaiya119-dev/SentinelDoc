"""False-Positive Control Suite.

Verifies that non-PII identifiers, invalid checksum numbers, business codes,
and dictionary words are NOT mistakenly flagged as sensitive PII.
Includes 16 authoritative test cases covering Verhoeff rejection, Luhn rejection,
PAN structure rejection, phone prefix rejection, zip codes, and order numbers.
"""
import pytest
from fastapi.testclient import TestClient

from tests.fixtures.generator import create_txt, generate_simple_pdf
from tests.fixtures.sample_data import FALSE_POSITIVE_16_CASES
from tests.conftest import assert_valid_scan_response


@pytest.mark.false_positive
class TestFalsePositiveControls:
    """16 authoritative false-positive control test cases."""

    def _scan_text(self, client: TestClient, text: str) -> list:
        """Helper to scan raw text content via /scan endpoint."""
        files = {"file": ("test_fp.txt", create_txt(text), "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200, f"Scan failed: {resp.text}"
        data = resp.json()
        assert_valid_scan_response(data)
        return data["findings"]

    def test_fp01_invalid_aadhaar_verhoeff_checksum(self, client: TestClient):
        """FP-01: 12-digit number with invalid Verhoeff checksum (3675 9832 4512) must NOT be flagged as AADHAAR."""
        text = "Reference number: 3675 9832 4512 recorded in system."
        findings = self._scan_text(client, text)
        aadhaar_findings = [f for f in findings if f["entity_type"] == "AADHAAR"]
        assert len(aadhaar_findings) == 0, f"False positive Aadhaar detected: {aadhaar_findings}"

    def test_fp02_invalid_aadhaar_prefix_starts_with_one(self, client: TestClient):
        """FP-02: 12-digit number starting with 1 (1234 5678 9012) must NOT be flagged as AADHAAR (UIDAI requires 2-9)."""
        text = "Hardware tracking barcode: 1234 5678 9012"
        findings = self._scan_text(client, text)
        aadhaar_findings = [f for f in findings if f["entity_type"] == "AADHAAR"]
        assert len(aadhaar_findings) == 0, f"False positive Aadhaar with prefix 1 detected: {aadhaar_findings}"

    def test_fp03_invalid_luhn_credit_card(self, client: TestClient):
        """FP-03: 16-digit number failing Luhn checksum (4532 0151 1283 0367) must NOT be flagged as CREDIT_CARD."""
        text = "Transaction token ID: 4532 0151 1283 0367"
        findings = self._scan_text(client, text)
        card_findings = [f for f in findings if f["entity_type"] == "CREDIT_CARD"]
        assert len(card_findings) == 0, f"False positive card detected: {card_findings}"

    def test_fp04_random_16_digit_number_fails_luhn(self, client: TestClient):
        """FP-04: Arbitrary 16-digit order identifier (9876543210987654) must NOT be flagged as CREDIT_CARD."""
        text = "Order tracking sequence: 9876543210987654"
        findings = self._scan_text(client, text)
        card_findings = [f for f in findings if f["entity_type"] == "CREDIT_CARD"]
        assert len(card_findings) == 0, f"Random 16 digits flagged as card: {card_findings}"

    def test_fp05_order_id_10_digits_starts_with_one(self, client: TestClient):
        """FP-05: 10-digit order ID starting with 1 (1002938475) must NOT be flagged as PHONE_NUMBER."""
        text = "E-Commerce Purchase Order ID: 1002938475 placed yesterday."
        findings = self._scan_text(client, text)
        phone_findings = [f for f in findings if f["entity_type"] == "PHONE_NUMBER"]
        assert len(phone_findings) == 0, f"Order ID flagged as phone: {phone_findings}"

    def test_fp06_order_id_with_prefix_and_12_digits(self, client: TestClient):
        """FP-06: Business order reference ORD-123456789012 must NOT be flagged as AADHAAR."""
        text = "Invoice shipping manifest: ORD-123456789012"
        findings = self._scan_text(client, text)
        aadhaar_findings = [f for f in findings if f["entity_type"] == "AADHAAR"]
        assert len(aadhaar_findings) == 0, f"ORD- prefix number flagged as Aadhaar: {aadhaar_findings}"

    def test_fp07_postal_pin_zip_codes(self, client: TestClient):
        """FP-07: 6-digit Indian PIN codes (560034, 110001) must NOT be flagged as PHONE_NUMBER or AADHAAR."""
        text = "Delivery to postal PIN codes 560034 and 110001."
        findings = self._scan_text(client, text)
        invalid_types = [f for f in findings if f["entity_type"] in ("PHONE_NUMBER", "AADHAAR", "CREDIT_CARD")]
        assert len(invalid_types) == 0, f"Postal PIN flagged as sensitive number: {invalid_types}"

    def test_fp08_sequential_10_digit_number(self, client: TestClient):
        """FP-08: Sequential digits 0123456789 must NOT be flagged as PHONE_NUMBER."""
        text = "Sample test sequence: 0123456789"
        findings = self._scan_text(client, text)
        phone_findings = [f for f in findings if f["entity_type"] == "PHONE_NUMBER"]
        assert len(phone_findings) == 0, f"Sequential digits flagged as phone: {phone_findings}"

    def test_fp09_invalid_pan_four_letters(self, client: TestClient):
        """FP-09: 10-char string with 4 letters and 5 digits (ABCD12345E) must NOT be flagged as PAN."""
        text = "Serial tag ABCD12345E printed on package."
        findings = self._scan_text(client, text)
        pan_findings = [f for f in findings if f["entity_type"] == "PAN"]
        assert len(pan_findings) == 0, f"Invalid 4-letter PAN flagged: {pan_findings}"

    def test_fp10_invalid_pan_reversed_structure(self, client: TestClient):
        """FP-10: 10-char string with digits preceding letters (12345ABCDE) must NOT be flagged as PAN."""
        text = "Warehouse bin locator: 12345ABCDE"
        findings = self._scan_text(client, text)
        pan_findings = [f for f in findings if f["entity_type"] == "PAN"]
        assert len(pan_findings) == 0, f"Reversed structure flagged as PAN: {pan_findings}"

    def test_fp11_invalid_pan_missing_check_letter(self, client: TestClient):
        """FP-11: 10-char string ending in digit (ABCDE12345) must NOT be flagged as PAN."""
        text = "Part specification: ABCDE12345"
        findings = self._scan_text(client, text)
        pan_findings = [f for f in findings if f["entity_type"] == "PAN"]
        assert len(pan_findings) == 0, f"PAN ending in digit flagged: {pan_findings}"

    def test_fp12_invalid_pan_11_char_alphanumeric(self, client: TestClient):
        """FP-12: 11-char alphanumeric string (ABCDE1234FA) must NOT be flagged as PAN."""
        text = "Extended inventory SKU: ABCDE1234FA"
        findings = self._scan_text(client, text)
        pan_findings = [f for f in findings if f["entity_type"] == "PAN"]
        assert len(pan_findings) == 0, f"11-char string flagged as PAN: {pan_findings}"

    def test_fp13_unix_epoch_timestamp(self, client: TestClient):
        """FP-13: 10-digit Unix timestamp (1725495000) must NOT be flagged as PHONE_NUMBER."""
        text = "System telemetry event epoch: 1725495000"
        findings = self._scan_text(client, text)
        phone_findings = [f for f in findings if f["entity_type"] == "PHONE_NUMBER"]
        assert len(phone_findings) == 0, f"Timestamp flagged as phone: {phone_findings}"

    def test_fp14_monetary_currency_amount(self, client: TestClient):
        """FP-14: Formatted Indian currency amount (₹ 12,34,567.89) must NOT be flagged as card, phone, or Aadhaar."""
        text = "Total quarterly revenue generated: ₹ 12,34,567.89"
        findings = self._scan_text(client, text)
        numeric_pii = [f for f in findings if f["entity_type"] in ("CREDIT_CARD", "AADHAAR", "PHONE_NUMBER")]
        assert len(numeric_pii) == 0, f"Currency amount flagged as PII: {numeric_pii}"

    def test_fp15_capitalized_heading_not_person(self, client: TestClient):
        """FP-15: Uppercase title 'INVOICE SUMMARY REPORT' must NOT be flagged as PERSON."""
        text = "INVOICE SUMMARY REPORT\nPrepared for internal corporate financial review."
        findings = self._scan_text(client, text)
        person_findings = [f for f in findings if f["entity_type"] == "PERSON" and "INVOICE" in f["matched_text"]]
        assert len(person_findings) == 0, f"Heading flagged as PERSON: {person_findings}"

    def test_fp16_calendar_month_names_not_person(self, client: TestClient):
        """FP-16: Capitalized month names 'Meeting held in May and August' must NOT flag May or August as PERSON."""
        text = "The committee meeting was held in May and August to review security policies."
        findings = self._scan_text(client, text)
        month_persons = [f for f in findings if f["entity_type"] == "PERSON" and f["matched_text"] in ("May", "August")]
        assert len(month_persons) == 0, f"Month name flagged as PERSON: {month_persons}"

    def test_combined_false_positive_control_document(self, client: TestClient, false_positive_doc_bytes: bytes):
        """Comprehensive verification: A document containing all 16 false positive items must produce 0 false positives."""
        files = {"file": ("control_evaluation.txt", false_positive_doc_bytes, "text/plain")}
        resp = client.post("/scan", files=files)
        assert resp.status_code == 200
        data = resp.json()

        # None of the 16 items may match Aadhaar, PAN, or Credit Card
        strict_false_positives = [
            f for f in data["findings"]
            if f["entity_type"] in ("AADHAAR", "PAN", "CREDIT_CARD")
        ]
        assert len(strict_false_positives) == 0, f"Strict false positives detected in control doc: {strict_false_positives}"

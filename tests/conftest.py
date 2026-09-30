"""Pytest configuration, shared fixtures, and TestClient harness for SentinelDoc E2E suite."""
import os
import io
import json
import pytest
from typing import Generator, Any
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
    generate_synthetic_resume_pdf,
    generate_synthetic_invoice_xlsx,
    generate_synthetic_customer_database_csv,
    generate_synthetic_confidential_memo_docx,
    generate_synthetic_server_audit_txt
)
from tests.fixtures.sample_data import FALSE_POSITIVE_16_CASES


def pytest_configure(config):
    """Register custom markers for the 4-tier dual-track test runner."""
    config.addinivalue_line("markers", "tier1: Tier 1 Feature Coverage Unit & Integration Tests")
    config.addinivalue_line("markers", "tier2: Tier 2 Boundary, Degenerate, & Extreme Coordinate Tests")
    config.addinivalue_line("markers", "tier3: Tier 3 Combinations, Partial Redactions, & Multi-Page Tests")
    config.addinivalue_line("markers", "tier4: Tier 4 Real-World Benchmark Scenario Tests")
    config.addinivalue_line("markers", "false_positive: False-Positive Control Suite Tests")


@pytest.fixture(scope="session")
def client() -> Generator[TestClient, None, None]:
    """Provide session-scoped FastAPI TestClient connected to SentinelDoc backend."""
    try:
        from app.main import app
        with TestClient(app) as test_client:
            yield test_client
    except ImportError as e:
        pytest.fail(f"Could not import FastAPI app from app.main: {e}")


def is_redact_implemented(client: TestClient) -> bool:
    """Check if /redact route is implemented in the current milestone build."""
    routes = [getattr(r, "path", None) for r in client.app.routes]
    return "/redact" in routes


# =====================================================================
# DOCUMENT FIXTURES
# =====================================================================

@pytest.fixture(scope="session")
def sample_pdf_bytes() -> bytes:
    """A standard PDF with planted Aadhaar, PAN, and Phone."""
    text = (
        "CONFIDENTIAL IDENTIFICATION RECORD\n"
        "Employee: Aarav Sharma\n"
        "Aadhaar Number: 3675 9832 4511\n"
        "Permanent Account Number: ABCPE1234F\n"
        "Mobile Number: +91 98765 43210\n"
        "Official Email: aarav.sharma@domain.com\n"
    )
    return generate_simple_pdf(text)


@pytest.fixture(scope="session")
def sample_docx_bytes() -> bytes:
    """A standard DOCX with planted PAN and Card number."""
    text = (
        "SENTINEL FINANCIAL SERVICES — CUSTOMER SUMMARY\n"
        "Name: Priya Ramanathan\n"
        "Tax Identifier (PAN): XYZCA5678B\n"
        "Primary Payment Card: 4532 0151 1283 0366\n"
        "Billing Address: Plot 12, Sector 18, Electronic City Phase 1, Bangalore 560100\n"
    )
    return generate_simple_docx(text)


@pytest.fixture(scope="session")
def sample_csv_bytes() -> bytes:
    """A standard CSV with planted PII."""
    header = ["id", "full_name", "email", "phone", "aadhaar"]
    rows = [
        [1, "Aarav Sharma", "aarav.sharma@domain.com", "+91 98765 43210", "3675 9832 4511"],
        [2, "Vikramaditya Mukherjee", "harsh.patel@sentineldoc.com", "9876543210", "4321-8765-2109"]
    ]
    return generate_simple_csv(header, rows)


@pytest.fixture(scope="session")
def sample_xlsx_bytes() -> bytes:
    """A standard XLSX with planted PII."""
    header = ["Emp ID", "Name", "Corporate Email", "PAN"]
    rows = [
        ["EMP-01", "Aarav Sharma", "aarav.sharma@domain.com", "ABCPE1234F"],
        ["EMP-02", "Priya Ramanathan", "compliance_officer+audit@enterprise.org.in", "XYZCA5678B"]
    ]
    return generate_simple_xlsx("Employees", header, rows)


@pytest.fixture(scope="session")
def sample_txt_bytes() -> bytes:
    """A standard TXT with planted PII."""
    content = (
        "Server incident report\n"
        "Operator: Aarav Sharma\n"
        "Contact: +91 98765 43210\n"
        "Email: harsh.patel@sentineldoc.com\n"
        "Card charged: 4532 0151 1283 0366\n"
    )
    return create_txt(content)


@pytest.fixture(scope="session")
def false_positive_doc_bytes() -> bytes:
    """A text document containing all 16 tricky non-PII test values."""
    lines = ["FALSE POSITIVE EVALUATION DOCUMENT - NO SENSITIVE DATA", ""]
    for case in FALSE_POSITIVE_16_CASES:
        lines.append(f"Case {case.case_id} ({case.category}): {case.raw_value}")
    return create_txt("\n".join(lines) + "\n")


@pytest.fixture(scope="session")
def synthetic_resume_pdf() -> bytes:
    return generate_synthetic_resume_pdf()


@pytest.fixture(scope="session")
def synthetic_invoice_xlsx() -> bytes:
    return generate_synthetic_invoice_xlsx()


@pytest.fixture(scope="session")
def synthetic_customer_csv() -> bytes:
    return generate_synthetic_customer_database_csv(50)


@pytest.fixture(scope="session")
def synthetic_memo_docx() -> bytes:
    return generate_synthetic_confidential_memo_docx()


@pytest.fixture(scope="session")
def synthetic_audit_txt() -> bytes:
    return generate_synthetic_server_audit_txt(500)


# =====================================================================
# ASSERTION HELPERS
# =====================================================================

def assert_valid_scan_response(data: dict):
    """Verify scan response adheres strictly to API contract."""
    assert "file_name" in data, "Response missing file_name"
    assert "file_type" in data, "Response missing file_type"
    assert "total_findings" in data, "Response missing total_findings"
    assert "findings" in data, "Response missing findings list"
    assert isinstance(data["findings"], list)
    assert data["total_findings"] == len(data["findings"])

    finding_ids = set()
    for f in data["findings"]:
        assert "id" in f, "Finding missing id"
        assert f["id"] not in finding_ids, f"Duplicate finding id: {f['id']}"
        finding_ids.add(f["id"])

        assert "entity_type" in f, "Finding missing entity_type"
        assert "matched_text" in f, "Finding missing matched_text"
        assert "confidence" in f, "Finding missing confidence"
        assert "reasoning" in f, "Finding missing reasoning"
        assert "location" in f, "Finding missing location"

        assert 0.0 <= f["confidence"] <= 1.0, f"Confidence out of range: {f['confidence']}"
        assert isinstance(f["reasoning"], str) and len(f["reasoning"].strip()) > 0, "Reasoning is empty"
        assert isinstance(f["location"], dict), "Location must be a dict"

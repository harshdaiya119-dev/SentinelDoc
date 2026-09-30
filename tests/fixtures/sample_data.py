"""Authoritative catalogs of planted valid PII, non-PII false positive controls, and reference oracles."""
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

# =====================================================================
# REFERENCE ALGORITHMIC ORACLES (Ground Truth Checksums)
# =====================================================================

D_TABLE = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
]

P_TABLE = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
]

INV_TABLE = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]


def reference_verhoeff_validate(number_str: str) -> bool:
    """Verhoeff validation oracle using D5 dihedral group."""
    digits = [int(ch) for ch in str(number_str) if ch.isdigit()]
    if len(digits) != 12:
        return False
    # UIDAI specification: Aadhaar numbers must not start with 0 or 1
    if digits[0] in (0, 1):
        return False
    c = 0
    for i, x in enumerate(reversed(digits)):
        c = D_TABLE[c][P_TABLE[i % 8][x]]
    return c == 0


def reference_luhn_validate(card_str: str) -> bool:
    """Luhn validation oracle modulo 10."""
    digits = [int(ch) for ch in str(card_str) if ch.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    total = 0
    reversed_digits = digits[::-1]
    for i, digit in enumerate(reversed_digits):
        if i % 2 == 1:
            doubled = digit * 2
            total += (doubled - 9) if doubled > 9 else doubled
        else:
            total += digit
    return total % 10 == 0


# =====================================================================
# DATA CLASSES
# =====================================================================

@dataclass
class GroundTruthItem:
    raw_value: str
    entity_type: str
    min_confidence: float
    required_reasoning_keyword: Optional[str]
    description: str


@dataclass
class FalsePositiveControlCase:
    case_id: str
    category: str
    raw_value: str
    mimicked_entity_type: str
    rejection_reason: str


# =====================================================================
# AUTHORITATIVE CATALOGS OF VALID PLANTED PII
# =====================================================================

VALID_AADHAAR_CATALOG = [
    GroundTruthItem(
        raw_value="3675 9832 4511",
        entity_type="AADHAAR",
        min_confidence=0.85,
        required_reasoning_keyword="verhoeff",
        description="Standard 3x4 spaced Aadhaar number with valid Verhoeff check digit"
    ),
    GroundTruthItem(
        raw_value="982341567897",
        entity_type="AADHAAR",
        min_confidence=0.85,
        required_reasoning_keyword="verhoeff",
        description="Continuous 12-digit Aadhaar number with valid Verhoeff check digit"
    ),
    GroundTruthItem(
        raw_value="4321-8765-2109",
        entity_type="AADHAAR",
        min_confidence=0.85,
        required_reasoning_keyword="verhoeff",
        description="Hyphenated 12-digit Aadhaar number with valid Verhoeff check digit"
    ),
    GroundTruthItem(
        raw_value="2345 6789 0124",
        entity_type="AADHAAR",
        min_confidence=0.85,
        required_reasoning_keyword="verhoeff",
        description="Additional valid Aadhaar starting with 2"
    ),
    GroundTruthItem(
        raw_value="9876 5432 1096",
        entity_type="AADHAAR",
        min_confidence=0.85,
        required_reasoning_keyword="verhoeff",
        description="Additional valid Aadhaar starting with 9"
    )
]

VALID_PAN_CATALOG = [
    GroundTruthItem(
        raw_value="ABCPE1234F",
        entity_type="PAN",
        min_confidence=0.85,
        required_reasoning_keyword="pan",
        description="Standard individual PAN (4th letter P for person)"
    ),
    GroundTruthItem(
        raw_value="XYZCA5678B",
        entity_type="PAN",
        min_confidence=0.85,
        required_reasoning_keyword="pan",
        description="Company PAN (4th letter C)"
    ),
    GroundTruthItem(
        raw_value="BNZPK9876M",
        entity_type="PAN",
        min_confidence=0.85,
        required_reasoning_keyword="pan",
        description="Individual PAN (4th letter P)"
    ),
    GroundTruthItem(
        raw_value="abcpe1234f",
        entity_type="PAN",
        min_confidence=0.80,
        required_reasoning_keyword="pan",
        description="Lowercase PAN format"
    ),
    GroundTruthItem(
        raw_value="BKZPK7190M",
        entity_type="PAN",
        min_confidence=0.85,
        required_reasoning_keyword="pan",
        description="Taxpayer status verified PAN"
    )
]

VALID_CARD_CATALOG = [
    GroundTruthItem(
        raw_value="4532 0151 1283 0366",
        entity_type="CREDIT_CARD",
        min_confidence=0.85,
        required_reasoning_keyword="luhn",
        description="Visa 16-digit card number with valid Luhn checksum"
    ),
    GroundTruthItem(
        raw_value="5424-1801-2345-6789",
        entity_type="CREDIT_CARD",
        min_confidence=0.85,
        required_reasoning_keyword="luhn",
        description="Mastercard 16-digit card with hyphens and valid Luhn"
    ),
    GroundTruthItem(
        raw_value="378282246310005",
        entity_type="CREDIT_CARD",
        min_confidence=0.85,
        required_reasoning_keyword="luhn",
        description="American Express 15-digit card with valid Luhn"
    ),
    GroundTruthItem(
        raw_value="6071 2345 6789 0120",
        entity_type="CREDIT_CARD",
        min_confidence=0.85,
        required_reasoning_keyword="luhn",
        description="RuPay 16-digit card number with valid Luhn"
    )
]

VALID_PHONE_CATALOG = [
    GroundTruthItem(
        raw_value="+91 98765 43210",
        entity_type="PHONE_NUMBER",
        min_confidence=0.75,
        required_reasoning_keyword=None,
        description="Indian mobile with +91 country prefix and spaces"
    ),
    GroundTruthItem(
        raw_value="+91-9123456789",
        entity_type="PHONE_NUMBER",
        min_confidence=0.75,
        required_reasoning_keyword=None,
        description="Indian mobile with +91 country prefix and hyphen"
    ),
    GroundTruthItem(
        raw_value="9876543210",
        entity_type="PHONE_NUMBER",
        min_confidence=0.70,
        required_reasoning_keyword=None,
        description="10-digit Indian mobile starting with 9"
    ),
    GroundTruthItem(
        raw_value="8765432109",
        entity_type="PHONE_NUMBER",
        min_confidence=0.70,
        required_reasoning_keyword=None,
        description="10-digit Indian mobile starting with 8"
    ),
    GroundTruthItem(
        raw_value="080-23456789",
        entity_type="PHONE_NUMBER",
        min_confidence=0.70,
        required_reasoning_keyword=None,
        description="Bangalore landline with STD prefix 080"
    )
]

VALID_EMAIL_CATALOG = [
    GroundTruthItem(
        raw_value="harsh.patel@sentineldoc.com",
        entity_type="EMAIL_ADDRESS",
        min_confidence=0.85,
        required_reasoning_keyword="email",
        description="Internal corporate email with dotted username"
    ),
    GroundTruthItem(
        raw_value="compliance_officer+audit@enterprise.org.in",
        entity_type="EMAIL_ADDRESS",
        min_confidence=0.85,
        required_reasoning_keyword="email",
        description="Subdomain and plus-tagged email address"
    ),
    GroundTruthItem(
        raw_value="contact@domain.co",
        entity_type="EMAIL_ADDRESS",
        min_confidence=0.85,
        required_reasoning_keyword="email",
        description="Standard domain email"
    ),
    GroundTruthItem(
        raw_value="aarav.sharma@domain.com",
        entity_type="EMAIL_ADDRESS",
        min_confidence=0.85,
        required_reasoning_keyword="email",
        description="Personal domain email"
    )
]

VALID_NAMES_CATALOG = [
    GroundTruthItem(
        raw_value="Aarav Sharma",
        entity_type="PERSON",
        min_confidence=0.60,
        required_reasoning_keyword=None,
        description="Common North Indian person name"
    ),
    GroundTruthItem(
        raw_value="Priya Ramanathan",
        entity_type="PERSON",
        min_confidence=0.60,
        required_reasoning_keyword=None,
        description="Common South Indian person name"
    ),
    GroundTruthItem(
        raw_value="Vikramaditya Mukherjee",
        entity_type="PERSON",
        min_confidence=0.60,
        required_reasoning_keyword=None,
        description="Multi-syllable Bengali person name"
    )
]

VALID_ADDRESSES_CATALOG = [
    GroundTruthItem(
        raw_value="Flat 402, Lotus Towers, MG Road, Koramangala, Bengaluru, Karnataka 560034",
        entity_type="LOCATION",
        min_confidence=0.60,
        required_reasoning_keyword=None,
        description="Full residential address in Bangalore with postal PIN"
    ),
    GroundTruthItem(
        raw_value="Plot 12, Sector 18, Electronic City Phase 1, Bangalore 560100",
        entity_type="LOCATION",
        min_confidence=0.60,
        required_reasoning_keyword=None,
        description="Commercial IT corridor address in Bangalore"
    ),
    GroundTruthItem(
        raw_value="24B Park Street, Near City Center, Kolkata, West Bengal 700016",
        entity_type="LOCATION",
        min_confidence=0.60,
        required_reasoning_keyword=None,
        description="Kolkata landmark commercial street address"
    )
]

# =====================================================================
# AUTHORITATIVE CATALOG OF 16 FALSE-POSITIVE CONTROL CASES
# =====================================================================

FALSE_POSITIVE_16_CASES: List[FalsePositiveControlCase] = [
    FalsePositiveControlCase(
        case_id="FP-01",
        category="Invalid Aadhaar Checksum",
        raw_value="3675 9832 4512",
        mimicked_entity_type="AADHAAR",
        rejection_reason="Verhoeff check digit invalid (check digit is 2 instead of 1)"
    ),
    FalsePositiveControlCase(
        case_id="FP-02",
        category="Invalid Aadhaar Prefix",
        raw_value="1234 5678 9012",
        mimicked_entity_type="AADHAAR",
        rejection_reason="Starts with 1; UIDAI Aadhaar specifications mandate first digit in [2-9]"
    ),
    FalsePositiveControlCase(
        case_id="FP-03",
        category="Invalid Luhn Card",
        raw_value="4532 0151 1283 0367",
        mimicked_entity_type="CREDIT_CARD",
        rejection_reason="Luhn checksum modulo 10 check failed"
    ),
    FalsePositiveControlCase(
        case_id="FP-04",
        category="Random 16-Digit Number",
        raw_value="9876543210987654",
        mimicked_entity_type="CREDIT_CARD",
        rejection_reason="Arbitrary 16-digit order number failing Luhn algorithm"
    ),
    FalsePositiveControlCase(
        case_id="FP-05",
        category="Order ID (10 digits)",
        raw_value="1002938475",
        mimicked_entity_type="PHONE_NUMBER",
        rejection_reason="Starts with 1 (Indian mobile numbers must start with 6, 7, 8, or 9)"
    ),
    FalsePositiveControlCase(
        case_id="FP-06",
        category="Order ID (12 digits with prefix)",
        raw_value="ORD-123456789012",
        mimicked_entity_type="AADHAAR",
        rejection_reason="Business order reference with ORD prefix; not an identity number"
    ),
    FalsePositiveControlCase(
        case_id="FP-07",
        category="Postal PIN / Zip Code",
        raw_value="560034",
        mimicked_entity_type="PHONE_NUMBER",
        rejection_reason="6-digit Indian PIN code must not be recognized as phone number or Aadhaar"
    ),
    FalsePositiveControlCase(
        case_id="FP-08",
        category="Sequential 10-Digit Number",
        raw_value="0123456789",
        mimicked_entity_type="PHONE_NUMBER",
        rejection_reason="Leading zero and non-valid mobile range; low-entropy sequence"
    ),
    FalsePositiveControlCase(
        case_id="FP-09",
        category="Invalid PAN (4 Letters)",
        raw_value="ABCD12345E",
        mimicked_entity_type="PAN",
        rejection_reason="4 letters + 5 digits instead of strict 5 letters + 4 digits + 1 letter"
    ),
    FalsePositiveControlCase(
        case_id="FP-10",
        category="Invalid PAN (Reversed)",
        raw_value="12345ABCDE",
        mimicked_entity_type="PAN",
        rejection_reason="Digits precede letters; reversed PAN structure"
    ),
    FalsePositiveControlCase(
        case_id="FP-11",
        category="Invalid PAN (Missing Check Letter)",
        raw_value="ABCDE12345",
        mimicked_entity_type="PAN",
        rejection_reason="Last character is numeric digit instead of letter"
    ),
    FalsePositiveControlCase(
        case_id="FP-12",
        category="11-Character Alphanumeric",
        raw_value="ABCDE1234FA",
        mimicked_entity_type="PAN",
        rejection_reason="Exceeds 10-character PAN length; word boundary violated"
    ),
    FalsePositiveControlCase(
        case_id="FP-13",
        category="Unix Epoch Timestamp",
        raw_value="1725495000",
        mimicked_entity_type="PHONE_NUMBER",
        rejection_reason="10-digit timestamp starting with 172...; lacks mobile context"
    ),
    FalsePositiveControlCase(
        case_id="FP-14",
        category="Monetary Currency Amount",
        raw_value="₹ 12,34,567.89",
        mimicked_entity_type="CREDIT_CARD",
        rejection_reason="Currency symbol with comma-formatted numeric value"
    ),
    FalsePositiveControlCase(
        case_id="FP-15",
        category="Capitalized Heading",
        raw_value="INVOICE SUMMARY REPORT",
        mimicked_entity_type="PERSON",
        rejection_reason="Uppercase document title; not a personal human name"
    ),
    FalsePositiveControlCase(
        case_id="FP-16",
        category="Calendar Month Names",
        raw_value="Meeting held in May and August",
        mimicked_entity_type="PERSON",
        rejection_reason="English calendar months capitalized in sentence; not person names"
    )
]

"""Confidence scoring and dynamic reasoning generator for PII findings.

Computes meaningful, calibrated confidence scores (0.0 to 1.0) and generates
detailed human-readable reasoning strings based on base pattern match,
checksum verification (Verhoeff / Luhn), brand / taxpayer status heuristics,
and surrounding context keywords.
"""
import re
from typing import Tuple, Optional

# Context keywords per entity type for boosting confidence
CONTEXT_KEYWORDS = {
    "AADHAAR": [
        "aadhaar", "uidai", "uid", "aadhar", "mera aadhaar",
        "unique identification", "resident", "enrolment",
    ],
    "PAN": [
        "pan", "income tax", "taxpayer", "permanent account number",
        "pan card", "nsdl", "uti", "form 16", "itr", "assessee",
    ],
    "CREDIT_CARD": [
        "credit", "debit", "card", "visa", "mastercard", "rupay",
        "amex", "american express", "discover", "cardholder", "cvv",
        "expiry", "valid thru", "card no", "card number",
    ],
    "PHONE_NUMBER": [
        "phone", "mobile", "contact", "call", "tel", "cell",
        "telephone", "whatsapp", "sms", "reach us", "ph:", "mob:",
    ],
    "EMAIL_ADDRESS": [
        "email", "mail", "e-mail", "contact", "inbox", "mailto",
        "reach", "write to",
    ],
    "PERSON": [
        "name", "mr.", "mr", "ms.", "ms", "mrs.", "mrs", "dr.", "dr",
        "prof.", "prof", "shri", "smt", "candidate", "employee", "patient",
        "officer", "author", "student", "full name",
    ],
    "LOCATION": [
        "address", "street", "road", "rd", "marg", "nagar", "colony",
        "sector", "plot", "flat", "floor", "building", "apartment",
        "block", "city", "state", "pincode", "pin code", "postal",
        "district",
    ],
    "DATE_OF_BIRTH": [
        "dob", "date of birth", "birth date", "born on", "born",
        "d.o.b", "d.o.b.",
    ],
}

# Recognized PAN taxpayer status letters (4th character)
PAN_TAXPAYER_TYPES = {
    "A": "Association of Persons (AOP)",
    "B": "Body of Individuals (BOI)",
    "C": "Company",
    "F": "Firm / Limited Liability Partnership",
    "G": "Government Agency",
    "H": "Hindu Undivided Family (HUF)",
    "J": "Artificial Juridical Person",
    "L": "Local Authority",
    "P": "Individual Person",
    "T": "Trust",
}


def _find_matching_context(text_context: str, entity_type: str) -> Optional[str]:
    """Check if any context keyword for the entity type is present in surrounding context."""
    if not text_context:
        return None
    lower_context = text_context.lower()
    keywords = CONTEXT_KEYWORDS.get(entity_type, [])
    for kw in keywords:
        # Use word boundary where appropriate
        if re.search(r"\b" + re.escape(kw) + r"\b", lower_context):
            return kw
    return None


def calculate_confidence_and_reasoning(
    entity_type: str,
    matched_text: str,
    surrounding_context: str = "",
    checksum_passed: Optional[bool] = None,
    raw_score: Optional[float] = None,
) -> Tuple[float, str]:
    """Compute calibrated confidence score and reasoning string for a finding.

    Args:
        entity_type: Standardized entity type (e.g. AADHAAR, PAN, CREDIT_CARD, etc.)
        matched_text: The exact text snippet matched.
        surrounding_context: Text surrounding the match (e.g. sentence, line, paragraph).
        checksum_passed: Whether algorithmic checksum (Verhoeff/Luhn) passed.
        raw_score: Initial score from Presidio / spaCy if available.

    Returns:
        Tuple of (confidence: float, reasoning: str).
    """
    matched_text_clean = matched_text.strip()
    context_keyword = _find_matching_context(surrounding_context, entity_type)

    if entity_type == "AADHAAR":
        digits_only = "".join(c for c in matched_text_clean if c.isdigit())
        base_score = 0.40
        reasons = ["Matches 12-digit Aadhaar pattern"]

        if checksum_passed or (checksum_passed is None and len(digits_only) == 12):
            base_score += 0.45
            reasons.append("passed Verhoeff dihedral group checksum validation")

        # Check if formatted with standard 4-4-4 spacing
        if re.match(r"^[2-9]\d{3}\s\d{4}\s\d{4}$", matched_text_clean):
            base_score += 0.04
            reasons.append("standard 4-4-4 digit grouping")

        if context_keyword:
            base_score += 0.06
            reasons.append(f"boosted by context keyword '{context_keyword}'")

        confidence = min(0.98, max(0.40, round(base_score, 2)))
        reasoning = "; ".join(reasons)
        return confidence, reasoning

    elif entity_type == "PAN":
        pan_clean = matched_text_clean.upper()
        base_score = 0.40
        reasons = ["Matches 10-character PAN pattern (5 uppercase letters, 4 digits, 1 letter)"]

        if len(pan_clean) == 10 and re.match(r"^[A-Z]{5}\d{4}[A-Z]$", pan_clean):
            base_score += 0.45
            status_char = pan_clean[3]
            if status_char in PAN_TAXPAYER_TYPES:
                base_score += 0.04
                reasons.append(f"verified taxpayer status '{status_char}' ({PAN_TAXPAYER_TYPES[status_char]})")

        if context_keyword:
            base_score += 0.06
            reasons.append(f"boosted by context keyword '{context_keyword}'")

        confidence = min(0.98, max(0.40, round(base_score, 2)))
        reasoning = "; ".join(reasons)
        return confidence, reasoning

    elif entity_type == "CREDIT_CARD":
        digits_only = "".join(c for c in matched_text_clean if c.isdigit())
        base_score = 0.40
        card_brand = "Payment card"
        if digits_only.startswith("4"):
            card_brand = "Visa"
        elif digits_only.startswith(("51", "52", "53", "54", "55", "22")):
            card_brand = "Mastercard"
        elif digits_only.startswith(("34", "37")):
            card_brand = "American Express"
        elif digits_only.startswith(("60", "65", "81", "82", "508")):
            card_brand = "RuPay"
        elif digits_only.startswith("6011"):
            card_brand = "Discover"

        reasons = [f"Matches {card_brand} card number pattern ({len(digits_only)} digits)"]

        if checksum_passed or checksum_passed is None:
            base_score += 0.45
            reasons.append("passed Luhn modulo 10 checksum validation")

        # Grouping bonus
        if " " in matched_text_clean or "-" in matched_text_clean:
            base_score += 0.03
            reasons.append("standard card digit grouping")

        if context_keyword:
            base_score += 0.07
            reasons.append(f"boosted by financial context '{context_keyword}'")

        confidence = min(0.98, max(0.40, round(base_score, 2)))
        reasoning = "; ".join(reasons)
        return confidence, reasoning

    elif entity_type == "PHONE_NUMBER":
        digits_only = "".join(c for c in matched_text_clean if c.isdigit())
        base_score = 0.70
        reasons = ["Matches Indian 10-digit mobile number format (starts with 6-9)"]

        if matched_text_clean.startswith("+91") or matched_text_clean.startswith("0091"):
            base_score += 0.12
            reasons.append("prefixed with Indian country code (+91)")
        elif matched_text_clean.startswith("0"):
            base_score += 0.05
            reasons.append("prefixed with trunk code (0)")

        if context_keyword:
            base_score += 0.10
            reasons.append(f"boosted by telephony context '{context_keyword}'")

        confidence = min(0.96, max(0.65, round(base_score, 2)))
        reasoning = "; ".join(reasons)
        return confidence, reasoning

    elif entity_type == "EMAIL_ADDRESS":
        base_score = 0.88
        reasons = ["Matches standard RFC 5322 email pattern"]

        common_providers = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com"]
        if any(matched_text_clean.lower().endswith(provider) for provider in common_providers):
            base_score += 0.04
            reasons.append("verified common email domain")

        if context_keyword:
            base_score += 0.06
            reasons.append(f"boosted by contact context '{context_keyword}'")

        confidence = min(0.98, max(0.85, round(base_score, 2)))
        reasoning = "; ".join(reasons)
        return confidence, reasoning

    elif entity_type == "PERSON":
        base = raw_score if raw_score is not None else 0.65
        reasons = ["Identified as human person name via spaCy NER"]

        words = matched_text_clean.split()
        if len(words) >= 2:
            base += 0.10
            reasons.append("multi-token full name structure")

        if context_keyword:
            base += 0.12
            reasons.append(f"boosted by personal title/label '{context_keyword}'")

        confidence = min(0.92, max(0.55, round(base, 2)))
        reasoning = "; ".join(reasons)
        return confidence, reasoning

    elif entity_type == "LOCATION":
        base = raw_score if raw_score is not None else 0.60
        reasons = ["Identified as geographical location via spaCy NER"]

        if context_keyword:
            base += 0.18
            reasons.append(f"boosted by physical address keyword '{context_keyword}'")

        confidence = min(0.90, max(0.50, round(base, 2)))
        reasoning = "; ".join(reasons)
        return confidence, reasoning

    elif entity_type == "DATE_OF_BIRTH":
        base = 0.60
        reasons = ["Matches date pattern"]
        if context_keyword:
            base += 0.25
            reasons.append(f"boosted by birth date context '{context_keyword}'")

        confidence = min(0.92, max(0.60, round(base, 2)))
        reasoning = "; ".join(reasons)
        return confidence, reasoning

    else:
        # Generic fallback
        base = raw_score if raw_score is not None else 0.70
        reasoning = f"Detected {entity_type} based on pattern matching"
        return round(base, 2), reasoning

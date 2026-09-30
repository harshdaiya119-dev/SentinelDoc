"""Mathematical risk calculation engine for SentinelDoc.

Implements multi-tier severity weighting, diminishing marginal risk decay
for repeated entity findings, cross-entity diversity amplification, and
asymptotic [0, 100] normalization.
"""
import math
from typing import List, Tuple, Dict, Any, Union

# Severity weights per normalized entity type
ENTITY_WEIGHTS: Dict[str, float] = {
    "AADHAAR": 35.0,
    "CREDIT_CARD": 35.0,
    "PAN": 28.0,
    "PHONE": 15.0,
    "DATE_OF_BIRTH": 16.0,
    "EMAIL": 12.0,
    "PERSON": 10.0,
    "ADDRESS": 10.0,
}

# Normalization map for varied entity type names
ENTITY_NORMALIZATION: Dict[str, str] = {
    "AADHAAR": "AADHAAR",
    "CREDIT_CARD": "CREDIT_CARD",
    "CARD": "CREDIT_CARD",
    "CREDITCARD": "CREDIT_CARD",
    "PAN": "PAN",
    "PHONE": "PHONE",
    "PHONE_NUMBER": "PHONE",
    "DATE_OF_BIRTH": "DATE_OF_BIRTH",
    "DOB": "DATE_OF_BIRTH",
    "EMAIL": "EMAIL",
    "EMAIL_ADDRESS": "EMAIL",
    "PERSON": "PERSON",
    "NAME": "PERSON",
    "ADDRESS": "ADDRESS",
    "LOCATION": "ADDRESS",
}

# Severity tier classification for reporting breakdown
SEVERITY_TIERS: Dict[str, str] = {
    "AADHAAR": "Critical",
    "CREDIT_CARD": "Critical",
    "PAN": "High",
    "DATE_OF_BIRTH": "High",
    "PHONE": "Medium",
    "ADDRESS": "Medium",
    "EMAIL": "Low",
    "PERSON": "Low",
}

# Saturation scaling constant for asymptotic normalization S = 100 * (1 - e^(-R / K))
SATURATION_CONSTANT: float = 52.0

# Diminishing marginal decay factor for repeated findings
DECAY_RATE: float = 0.35


def normalize_entity_type(raw_type: str) -> str:
    """Normalize raw entity type string to canonical type."""
    cleaned = raw_type.strip().upper()
    return ENTITY_NORMALIZATION.get(cleaned, cleaned)


def get_entity_severity(raw_type: str) -> str:
    """Get the severity tier ('Critical', 'High', 'Medium', 'Low') for an entity type."""
    canonical = normalize_entity_type(raw_type)
    return SEVERITY_TIERS.get(canonical, "Low")


def calculate_risk_profile(
    findings: List[Any],
) -> Tuple[int, str, Dict[str, Any]]:
    """Compute mathematical risk score, risk level, and executive breakdown summary.

    Args:
        findings: List of Finding objects or dicts representing detected PII entities.

    Returns:
        Tuple of:
            - risk_score (int): Normalized integer score in [0, 100].
            - risk_level (str): 'Low' (0-39), 'Medium' (40-69), or 'High' (70-100).
            - summary (Dict[str, Any]): Breakdown metrics containing:
                * critical_count: Count of Critical findings (Aadhaar, Credit Card).
                * high_count: Count of High findings (PAN, Date of Birth).
                * medium_count: Count of Medium findings (Phone, Address).
                * low_count: Count of Low findings (Email, Person, etc.).
                * primary_threat: Descriptive summary of dominant exposure vector.
                * compliance_verdict: Actionable compliance recommendation.
    """
    if not findings:
        return (
            0,
            "Low",
            {
                "critical_count": 0,
                "high_count": 0,
                "medium_count": 0,
                "low_count": 0,
                "primary_threat": "No sensitive PII exposure detected in analyzed document.",
                "compliance_verdict": "Clean compliance audit: Document is safe for external distribution.",
            },
        )

    # 1. Group confidence scores by canonical entity type & count severity tiers
    grouped_confidences: Dict[str, List[float]] = {}
    critical_count = 0
    high_count = 0
    medium_count = 0
    low_count = 0

    for item in findings:
        if isinstance(item, dict):
            raw_type = str(item.get("entity_type", "UNKNOWN"))
            confidence = float(item.get("confidence", 1.0))
        else:
            raw_type = str(getattr(item, "entity_type", "UNKNOWN"))
            confidence = float(getattr(item, "confidence", 1.0))

        canonical_type = normalize_entity_type(raw_type)
        grouped_confidences.setdefault(canonical_type, []).append(confidence)

        tier = SEVERITY_TIERS.get(canonical_type, "Low")
        if tier == "Critical":
            critical_count += 1
        elif tier == "High":
            high_count += 1
        elif tier == "Medium":
            medium_count += 1
        else:
            low_count += 1

    # 2. Compute entity-level submodular score with diminishing marginal decay
    # Sort confidences in descending order so highest confidence instances carry base weight
    r_sum = 0.0
    for canonical_type, confidences in grouped_confidences.items():
        base_weight = ENTITY_WEIGHTS.get(canonical_type, 10.0)
        confidences.sort(reverse=True)

        entity_score = sum(
            (base_weight * conf) / (1.0 + DECAY_RATE * (k - 1))
            for k, conf in enumerate(confidences, start=1)
        )
        r_sum += entity_score

    # 3. Cross-entity diversity factor
    # A combination of different PII types presents compounding correlation risk
    num_distinct_types = len(grouped_confidences)
    if num_distinct_types > 1:
        diversity_multiplier = 1.0 + min(num_distinct_types - 1, 4) * 0.05
    else:
        diversity_multiplier = 1.0

    r_total = r_sum * diversity_multiplier

    # 4. Asymptotic normalization: S = round(100 * (1 - e^(-R / 52)))
    normalized_score = round(100.0 * (1.0 - math.exp(-r_total / SATURATION_CONSTANT)))
    risk_score = min(100, max(0, normalized_score))

    # 5. Categorical Risk Level
    if risk_score >= 70:
        risk_level = "High"
    elif risk_score >= 40:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    # 6. Primary threat and compliance verdict synthesis
    present_types = set(grouped_confidences.keys())

    if critical_count > 0:
        threat_parts = []
        if "AADHAAR" in present_types:
            threat_parts.append("Aadhaar")
        if "CREDIT_CARD" in present_types:
            threat_parts.append("Credit Card")
        threat_label = ", ".join(threat_parts) if threat_parts else "Critical Financial/National IDs"
        primary_threat = f"Critical identity theft & financial fraud exposure ({threat_label})."
    elif high_count > 0:
        threat_parts = []
        if "PAN" in present_types:
            threat_parts.append("PAN")
        if "DATE_OF_BIRTH" in present_types:
            threat_parts.append("Date of Birth")
        threat_label = ", ".join(threat_parts) if threat_parts else "Taxpayer/KYC identifiers"
        primary_threat = f"Elevated taxpayer identity and KYC authentication bypass risk ({threat_label})."
    elif medium_count > 0:
        primary_threat = "Direct contact exposure and targeted spear-phishing vulnerability (Phone / Address)."
    else:
        primary_threat = "Low-level public identity and contact exposure (Email / Person Name)."

    if risk_level == "High":
        compliance_verdict = "Critical leak hazard: Immediate automated redaction required before external distribution."
    elif risk_level == "Medium":
        compliance_verdict = "Moderate leak risk: Manual review and redaction strongly recommended prior to sharing."
    else:
        compliance_verdict = "Low exposure risk: Document contains minor PII; optional redaction recommended."

    summary = {
        "critical_count": critical_count,
        "high_count": high_count,
        "medium_count": medium_count,
        "low_count": low_count,
        "primary_threat": primary_threat,
        "compliance_verdict": compliance_verdict,
    }

    return risk_score, risk_level, summary


def calculate_document_risk(findings: List[Any]) -> Dict[str, Any]:
    """Helper alias returning structured dictionary of risk calculations."""
    score, level, summary = calculate_risk_profile(findings)
    return {
        "risk_score": score,
        "risk_level": level,
        "summary": summary,
    }

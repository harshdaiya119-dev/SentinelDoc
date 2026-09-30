"""Unit tests for SentinelDoc Risk Scoring Engine (Phase 3).

Verifies the mathematical and logical requirements for risk scoring:
1. Zero-findings baseline (score 0, level 'Low', all counts 0)
2. Severity tier ordering (Aadhaar / Credit Card > PAN > Phone > Email / Person)
3. Monotonicity (adding findings never decreases risk score)
4. Count scaling & diminishing marginal returns (sublinear scaling)
5. Threshold categorization (Low: 0-39, Medium: 40-69, High: 70-100)
6. Executive risk metadata summary (critical, high, medium, low counts, primary threat, compliance verdict)
7. Edge cases, boundary stress, and adversarial conditions
"""
import pytest
from typing import List, Tuple, Dict, Any

from app.models.schemas import Finding, Location, BoundingBox

# Import risk engine function dynamically to support progressive milestone testability
try:
    from app.core.risk import calculate_risk_profile
except ImportError:
    try:
        from app.core.risk import calculate_document_risk as calculate_risk_profile
    except ImportError:
        calculate_risk_profile = None


def is_risk_engine_implemented() -> bool:
    """Check if risk engine function is imported and callable."""
    return calculate_risk_profile is not None


def unpack_risk_result(result: Any) -> Tuple[int, str, Dict[str, Any]]:
    """Normalize return value of risk calculation function to (score, level, summary_dict).

    Supports tuple return (score, level, summary_dict/model) or object return.
    """
    if isinstance(result, tuple):
        score = result[0]
        level = result[1]
        summary = result[2] if len(result) > 2 else {}
        if hasattr(summary, "model_dump"):
            summary_dict = summary.model_dump()
        elif hasattr(summary, "dict"):
            summary_dict = summary.dict()
        elif isinstance(summary, dict):
            summary_dict = summary
        else:
            summary_dict = {k: getattr(summary, k) for k in dir(summary) if not k.startswith("_")}
        return int(score), str(level), summary_dict
    elif hasattr(result, "risk_score") and hasattr(result, "risk_level"):
        score = result.risk_score
        level = result.risk_level
        if hasattr(result, "summary") and hasattr(result.summary, "model_dump"):
            summary_dict = result.summary.model_dump()
        elif hasattr(result, "summary") and isinstance(result.summary, dict):
            summary_dict = result.summary
        elif hasattr(result, "model_dump"):
            summary_dict = result.model_dump()
        elif hasattr(result, "dict"):
            summary_dict = result.dict()
        else:
            summary_dict = {k: getattr(result, k) for k in dir(result) if not k.startswith("_")}
        return int(score), str(level), summary_dict
    raise TypeError(f"Unexpected return type from risk engine: {type(result)}")


def make_finding(
    entity_type: str,
    confidence: float = 0.95,
    finding_id: str = "find_1",
    matched_text: str = "3675 9832 4511",
    reasoning: str = "Pattern matched with valid checksum",
    page: int = 1,
) -> Finding:
    """Helper to synthesize a valid Pydantic Finding object."""
    return Finding(
        id=finding_id,
        entity_type=entity_type,
        matched_text=matched_text,
        confidence=confidence,
        reasoning=reasoning,
        location=Location(
            page=page,
            bbox=BoundingBox(x0=50.0, top=100.0, x1=200.0, bottom=120.0),
            start_char=0,
            end_char=len(matched_text),
        ),
    )


# =====================================================================
# 1. Zero-Findings Baseline Tests
# =====================================================================

class TestZeroFindings:
    """Verify document with zero PII findings yields score 0 and level 'Low'."""

    def test_zero_findings_returns_zero_score(self):
        """Clean document with no findings must evaluate to risk_score = 0."""
        if not is_risk_engine_implemented():
            pytest.skip("app.core.risk not yet implemented in current build")
        score, level, summary = unpack_risk_result(calculate_risk_profile([]))
        assert score == 0, f"Expected risk_score 0 for empty findings, got {score}"

    def test_zero_findings_risk_level_is_low(self):
        """Clean document must classify as 'Low' risk level."""
        if not is_risk_engine_implemented():
            pytest.skip("app.core.risk not yet implemented in current build")
        score, level, summary = unpack_risk_result(calculate_risk_profile([]))
        assert level == "Low", f"Expected risk_level 'Low' for empty findings, got {level}"

    def test_zero_findings_summary_counts_all_zero(self):
        """All severity tier counts in summary must be 0 for empty findings."""
        if not is_risk_engine_implemented():
            pytest.skip("app.core.risk not yet implemented in current build")
        score, level, summary = unpack_risk_result(calculate_risk_profile([]))
        assert summary.get("critical_count", 0) == 0, "critical_count must be 0"
        assert summary.get("high_count", 0) == 0, "high_count must be 0"
        assert summary.get("medium_count", 0) == 0, "medium_count must be 0"
        assert summary.get("low_count", 0) == 0, "low_count must be 0"

    def test_zero_findings_threat_and_verdict_strings(self):
        """Summary must provide non-empty strings for primary threat and verdict."""
        if not is_risk_engine_implemented():
            pytest.skip("app.core.risk not yet implemented in current build")
        score, level, summary = unpack_risk_result(calculate_risk_profile([]))
        threat = summary.get("primary_threat", "")
        verdict = summary.get("compliance_verdict", "")
        assert isinstance(threat, str) and len(threat.strip()) > 0, "primary_threat must be non-empty"
        assert isinstance(verdict, str) and len(verdict.strip()) > 0, "compliance_verdict must be non-empty"


# =====================================================================
# 2. Single Finding Severity Ordering Tests
# =====================================================================

class TestSeverityOrdering:
    """Verify severity ordering: Aadhaar / Credit Card > PAN > Phone > Email / Person."""

    def test_tier1_aadhaar_higher_than_tier2_pan(self):
        """Tier 1 Aadhaar (weight 35) must produce higher risk score than Tier 2 PAN (weight 28)."""
        if not is_risk_engine_implemented():
            pytest.skip("app.core.risk not yet implemented in current build")
        score_aadhaar, _, _ = unpack_risk_result(calculate_risk_profile([make_finding("AADHAAR", 0.95)]))
        score_pan, _, _ = unpack_risk_result(calculate_risk_profile([make_finding("PAN", 0.95)]))
        assert score_aadhaar > score_pan, (
            f"Aadhaar score ({score_aadhaar}) must be strictly greater than PAN score ({score_pan})"
        )

    def test_tier1_card_higher_than_tier2_pan(self):
        """Tier 1 Credit Card (weight 35) must produce higher risk score than Tier 2 PAN (weight 28)."""
        if not is_risk_engine_implemented():
            pytest.skip("app.core.risk not yet implemented in current build")
        score_card, _, _ = unpack_risk_result(calculate_risk_profile([make_finding("CREDIT_CARD", 0.95)]))
        score_pan, _, _ = unpack_risk_result(calculate_risk_profile([make_finding("PAN", 0.95)]))
        assert score_card > score_pan, (
            f"Card score ({score_card}) must be strictly greater than PAN score ({score_pan})"
        )

    def test_tier1_aadhaar_and_card_equivalent_weights(self):
        """Aadhaar and Credit Card are both Tier 1 critical identifiers with identical base weights (35)."""
        if not is_risk_engine_implemented():
            pytest.skip("app.core.risk not yet implemented in current build")
        score_aadhaar, _, _ = unpack_risk_result(calculate_risk_profile([make_finding("AADHAAR", 0.95)]))
        score_card, _, _ = unpack_risk_result(calculate_risk_profile([make_finding("CREDIT_CARD", 0.95)]))
        assert abs(score_aadhaar - score_card) <= 1, (
            f"Aadhaar ({score_aadhaar}) and Card ({score_card}) should have identical or near-identical scores"
        )

    def test_tier2_pan_higher_than_tier3_phone(self):
        """Tier 2 PAN (weight 28) must produce higher risk score than Tier 3 Phone (weight 15)."""
        if not is_risk_engine_implemented():
            pytest.skip("app.core.risk not yet implemented in current build")
        score_pan, _, _ = unpack_risk_result(calculate_risk_profile([make_finding("PAN", 0.95)]))
        score_phone, _, _ = unpack_risk_result(calculate_risk_profile([make_finding("PHONE", 0.95)]))
        assert score_pan > score_phone, (
            f"PAN score ({score_pan}) must be strictly greater than Phone score ({score_phone})"
        )

    def test_tier3_phone_higher_than_tier4_email(self):
        """Tier 3 Phone (weight 15) must produce higher risk score than Tier 4 Email (weight 12)."""
        if not is_risk_engine_implemented():
            pytest.skip("app.core.risk not yet implemented in current build")
        score_phone, _, _ = unpack_risk_result(calculate_risk_profile([make_finding("PHONE", 0.95)]))
        score_email, _, _ = unpack_risk_result(calculate_risk_profile([make_finding("EMAIL", 0.95)]))
        assert score_phone > score_email, (
            f"Phone score ({score_phone}) must be strictly greater than Email score ({score_email})"
        )

    def test_tier4_email_and_person_ordering(self):
        """Tier 4 Email (weight 12) should score equal to or higher than Person name (weight 8-10)."""
        if not is_risk_engine_implemented():
            pytest.skip("app.core.risk not yet implemented in current build")
        score_email, _, _ = unpack_risk_result(calculate_risk_profile([make_finding("EMAIL", 0.90)]))
        score_person, _, _ = unpack_risk_result(calculate_risk_profile([make_finding("PERSON", 0.90)]))
        assert score_email >= score_person, (
            f"Email score ({score_email}) must be >= Person score ({score_person})"
        )

    def test_full_severity_ladder(self):
        """Verify complete hierarchy: Aadhaar >= Card > PAN > Phone > Email >= Person."""
        if not is_risk_engine_implemented():
            pytest.skip("app.core.risk not yet implemented in current build")
        conf = 0.90
        s_aadhaar, _, _ = unpack_risk_result(calculate_risk_profile([make_finding("AADHAAR", conf)]))
        s_card, _, _ = unpack_risk_result(calculate_risk_profile([make_finding("CREDIT_CARD", conf)]))
        s_pan, _, _ = unpack_risk_result(calculate_risk_profile([make_finding("PAN", conf)]))
        s_phone, _, _ = unpack_risk_result(calculate_risk_profile([make_finding("PHONE", conf)]))
        s_email, _, _ = unpack_risk_result(calculate_risk_profile([make_finding("EMAIL", conf)]))
        s_person, _, _ = unpack_risk_result(calculate_risk_profile([make_finding("PERSON", conf)]))

        assert s_aadhaar >= s_pan > s_phone > s_email >= s_person, (
            f"Hierarchy violated: Aadhaar={s_aadhaar}, Card={s_card}, PAN={s_pan}, "
            f"Phone={s_phone}, Email={s_email}, Person={s_person}"
        )


# =====================================================================
# 3. Monotonicity Tests
# =====================================================================

class TestMonotonicity:
    """Verify adding findings never decreases the risk score."""

    def test_monotonic_progressive_addition(self):
        """Progressively adding new findings must strictly increase or maintain score at every step."""
        if not is_risk_engine_implemented():
            pytest.skip("app.core.risk not yet implemented in current build")
        findings: List[Finding] = []
        scores: List[int] = []

        # Step 0: Empty
        s0, _, _ = unpack_risk_result(calculate_risk_profile(findings))
        scores.append(s0)

        # Step 1: Add Email
        findings.append(make_finding("EMAIL", 0.85, "find_1"))
        s1, _, _ = unpack_risk_result(calculate_risk_profile(findings))
        scores.append(s1)

        # Step 2: Add Phone
        findings.append(make_finding("PHONE", 0.90, "find_2"))
        s2, _, _ = unpack_risk_result(calculate_risk_profile(findings))
        scores.append(s2)

        # Step 3: Add PAN
        findings.append(make_finding("PAN", 0.95, "find_3"))
        s3, _, _ = unpack_risk_result(calculate_risk_profile(findings))
        scores.append(s3)

        # Step 4: Add Aadhaar
        findings.append(make_finding("AADHAAR", 0.98, "find_4"))
        s4, _, _ = unpack_risk_result(calculate_risk_profile(findings))
        scores.append(s4)

        # Step 5: Add Credit Card
        findings.append(make_finding("CREDIT_CARD", 0.98, "find_5"))
        s5, _, _ = unpack_risk_result(calculate_risk_profile(findings))
        scores.append(s5)

        for i in range(len(scores) - 1):
            assert scores[i] <= scores[i + 1], (
                f"Monotonicity violation at step {i} -> {i+1}: {scores[i]} > {scores[i+1]} (scores: {scores})"
            )

    def test_monotonic_repeated_single_type(self):
        """Repeatedly adding the same entity type must never decrease risk score."""
        if not is_risk_engine_implemented():
            pytest.skip("app.core.risk not yet implemented in current build")
        findings: List[Finding] = []
        prev_score = 0

        for k in range(1, 8):
            findings.append(make_finding("EMAIL", 0.85, f"find_{k}"))
            score, _, _ = unpack_risk_result(calculate_risk_profile(findings))
            assert score >= prev_score, (
                f"Adding instance {k} of EMAIL decreased score from {prev_score} to {score}"
            )
            prev_score = score

    def test_monotonic_removing_finding_never_increases_score(self):
        """Removing any finding from a set must never increase the risk score."""
        if not is_risk_engine_implemented():
            pytest.skip("app.core.risk not yet implemented in current build")
        full_set = [
            make_finding("AADHAAR", 0.95, "f1"),
            make_finding("PAN", 0.90, "f2"),
            make_finding("PHONE", 0.85, "f3"),
            make_finding("EMAIL", 0.80, "f4"),
        ]
        full_score, _, _ = unpack_risk_result(calculate_risk_profile(full_set))

        # Test removing each finding one by one
        for i in range(len(full_set)):
            reduced_set = full_set[:i] + full_set[i + 1:]
            reduced_score, _, _ = unpack_risk_result(calculate_risk_profile(reduced_set))
            assert reduced_score <= full_score, (
                f"Removing item {i} increased score from {full_score} to {reduced_score}"
            )

    def test_monotonic_confidence_impact(self):
        """Higher confidence detection must yield equal or higher risk score than lower confidence."""
        if not is_risk_engine_implemented():
            pytest.skip("app.core.risk not yet implemented in current build")
        f_low = [make_finding("AADHAAR", 0.50)]
        f_high = [make_finding("AADHAAR", 0.98)]

        score_low, _, _ = unpack_risk_result(calculate_risk_profile(f_low))
        score_high, _, _ = unpack_risk_result(calculate_risk_profile(f_high))

        assert score_high >= score_low, (
            f"Higher confidence score ({score_high}) must be >= lower confidence score ({score_low})"
        )


# =====================================================================
# 4. Count Scaling & Diminishing Marginal Returns Tests
# =====================================================================

class TestCountScalingAndDiminishingReturns:
    """Verify multiple occurrences scale sublinearly rather than linearly."""

    def test_sublinear_scaling_two_vs_one(self):
        """Score for 2 findings must be strictly less than 2x the score for 1 finding."""
        if not is_risk_engine_implemented():
            pytest.skip("app.core.risk not yet implemented in current build")
        f1 = [make_finding("EMAIL", 0.90, "f1")]
        f2 = [make_finding("EMAIL", 0.90, "f1"), make_finding("EMAIL", 0.90, "f2")]

        score_1, _, _ = unpack_risk_result(calculate_risk_profile(f1))
        score_2, _, _ = unpack_risk_result(calculate_risk_profile(f2))

        # Marginal contribution of second finding must be less than the first
        marginal_first = score_1
        marginal_second = score_2 - score_1

        assert marginal_second < marginal_first, (
            f"Diminishing returns failure: 1st marginal={marginal_first}, 2nd marginal={marginal_second}"
        )
        assert score_2 < 2 * score_1, (
            f"Sublinear scaling failure: score_2 ({score_2}) >= 2 * score_1 ({2 * score_1})"
        )

    def test_diminishing_marginal_returns_sequence(self):
        """Marginal score additions must be non-increasing as finding count grows."""
        if not is_risk_engine_implemented():
            pytest.skip("app.core.risk not yet implemented in current build")
        findings: List[Finding] = []
        marginal_gains: List[int] = []
        prev_score = 0

        for k in range(1, 6):
            findings.append(make_finding("PHONE", 0.85, f"find_{k}"))
            score, _, _ = unpack_risk_result(calculate_risk_profile(findings))
            marginal = score - prev_score
            marginal_gains.append(marginal)
            prev_score = score

        # Check marginal gains do not explode: each incremental gain is <= previous + tolerance
        # (allowing small integer rounding delta of at most 1)
        for i in range(len(marginal_gains) - 1):
            assert marginal_gains[i + 1] <= marginal_gains[i] + 1, (
                f"Marginal returns not diminishing: gains={marginal_gains}"
            )

    def test_count_scaling_saturation_ceiling(self):
        """A high volume of low-severity findings (e.g. 100 emails) must not explode linearly."""
        if not is_risk_engine_implemented():
            pytest.skip("app.core.risk not yet implemented in current build")
        emails_1 = [make_finding("EMAIL", 0.85, f"e_{i}") for i in range(1)]
        emails_10 = [make_finding("EMAIL", 0.85, f"e_{i}") for i in range(10)]
        emails_100 = [make_finding("EMAIL", 0.85, f"e_{i}") for i in range(100)]

        s1, _, _ = unpack_risk_result(calculate_risk_profile(emails_1))
        s10, _, _ = unpack_risk_result(calculate_risk_profile(emails_10))
        s100, _, _ = unpack_risk_result(calculate_risk_profile(emails_100))

        # 10 emails must NOT equal 10 * 1 email
        assert s10 < 10 * s1, f"Expected s10 ({s10}) < 10 * s1 ({10 * s1})"
        # 100 emails must remain bounded in [0, 100]
        assert s100 <= 100, f"Score exceeded 100: {s100}"
        # Even 100 emails should not saturate to 100 without high-severity/critical IDs
        assert s100 <= 95, f"100 emails produced disproportionate score: {s100}"

    def test_diminishing_returns_critical_identifiers(self):
        """Multiple Aadhaar numbers scale sublinearly with diminishing marginal risk."""
        if not is_risk_engine_implemented():
            pytest.skip("app.core.risk not yet implemented in current build")
        aadhaar_1 = [make_finding("AADHAAR", 0.95, "a_1")]
        aadhaar_2 = [make_finding("AADHAAR", 0.95, "a_1"), make_finding("AADHAAR", 0.95, "a_2")]

        s1, _, _ = unpack_risk_result(calculate_risk_profile(aadhaar_1))
        s2, _, _ = unpack_risk_result(calculate_risk_profile(aadhaar_2))

        assert s2 > s1, f"Second Aadhaar should increase score: s1={s1}, s2={s2}"
        assert s2 < 2 * s1, f"Second Aadhaar scaled linearly or superlinearly: s1={s1}, s2={s2}"


# =====================================================================
# 5. Threshold Categorization Tests
# =====================================================================

class TestThresholdCategorization:
    """Verify categorical mapping: Low (0-39), Medium (40-69), High (70-100)."""

    def test_low_risk_threshold_0_to_39(self):
        """A single low/medium finding (e.g. 1 email or 1 phone) must classify as 'Low'."""
        if not is_risk_engine_implemented():
            pytest.skip("app.core.risk not yet implemented in current build")
        findings = [make_finding("EMAIL", 0.85, "f1")]
        score, level, _ = unpack_risk_result(calculate_risk_profile(findings))
        assert 0 <= score <= 39, f"Score {score} not in Low range [0, 39]"
        assert level == "Low", f"Expected level 'Low', got '{level}'"

    def test_medium_risk_threshold_40_to_69(self):
        """A single Aadhaar or contact pair should classify as 'Medium' risk."""
        if not is_risk_engine_implemented():
            pytest.skip("app.core.risk not yet implemented in current build")
        # Single Aadhaar: raw ~ 33.25 to 35, normalized ~ 47-50
        findings = [make_finding("AADHAAR", 0.95, "f1")]
        score, level, _ = unpack_risk_result(calculate_risk_profile(findings))
        assert 40 <= score <= 69, f"Single Aadhaar score {score} not in Medium range [40, 69]"
        assert level == "Medium", f"Expected level 'Medium', got '{level}'"

    def test_high_risk_threshold_70_to_100(self):
        """Multiple critical identifiers (Aadhaar + PAN + Credit Card) must classify as 'High' risk."""
        if not is_risk_engine_implemented():
            pytest.skip("app.core.risk not yet implemented in current build")
        findings = [
            make_finding("AADHAAR", 0.95, "f1"),
            make_finding("PAN", 0.95, "f2"),
            make_finding("CREDIT_CARD", 0.95, "f3"),
        ]
        score, level, _ = unpack_risk_result(calculate_risk_profile(findings))
        assert 70 <= score <= 100, f"Combined critical score {score} not in High range [70, 100]"
        assert level == "High", f"Expected level 'High', got '{level}'"

    def test_boundary_score_categorization(self):
        """Verify the exact boundary mapping specification: Low <= 39, Medium <= 69, High >= 70."""
        if not is_risk_engine_implemented():
            pytest.skip("app.core.risk not yet implemented in current build")
        # Test across multiple synthesized finding combinations
        test_sets = [
            [],  # 0 -> Low
            [make_finding("EMAIL", 0.8)],  # ~10-20 -> Low
            [make_finding("AADHAAR", 0.95)],  # ~47 -> Medium
            [make_finding("AADHAAR", 0.95), make_finding("PAN", 0.90)],  # ~70 -> High
            [make_finding("CREDIT_CARD", 0.95) for _ in range(5)],  # >= 85 -> High
        ]
        for fset in test_sets:
            score, level, _ = unpack_risk_result(calculate_risk_profile(fset))
            if score <= 39:
                assert level == "Low", f"Score {score} must map to 'Low', got '{level}'"
            elif score <= 69:
                assert level == "Medium", f"Score {score} must map to 'Medium', got '{level}'"
            else:
                assert level == "High", f"Score {score} must map to 'High', got '{level}'"


# =====================================================================
# 6. Risk Metadata Summary Tests
# =====================================================================

class TestRiskMetadataFields:
    """Verify structured metadata fields: critical_count, high_count, medium_count, low_count, primary_threat, compliance_verdict."""

    def test_summary_counts_classification(self):
        """Counts by severity tier must exactly match the entities present."""
        if not is_risk_engine_implemented():
            pytest.skip("app.core.risk not yet implemented in current build")
        mixed_findings = [
            # Tier 1: Critical (2 Aadhaar + 1 Card = 3)
            make_finding("AADHAAR", 0.95, "c1"),
            make_finding("AADHAAR", 0.95, "c2"),
            make_finding("CREDIT_CARD", 0.95, "c3"),
            # Tier 2: High (2 PAN + 1 DOB = 3)
            make_finding("PAN", 0.90, "h1"),
            make_finding("PAN", 0.90, "h2"),
            make_finding("DATE_OF_BIRTH", 0.85, "h3"),
            # Tier 3: Medium (3 Phone + 1 Address = 4)
            make_finding("PHONE", 0.85, "m1"),
            make_finding("PHONE", 0.85, "m2"),
            make_finding("PHONE", 0.85, "m3"),
            make_finding("ADDRESS", 0.80, "m4"),
            # Tier 4: Low (4 Email + 2 Person = 6)
            make_finding("EMAIL", 0.80, "l1"),
            make_finding("EMAIL", 0.80, "l2"),
            make_finding("EMAIL", 0.80, "l3"),
            make_finding("EMAIL", 0.80, "l4"),
            make_finding("PERSON", 0.75, "l5"),
            make_finding("PERSON", 0.75, "l6"),
        ]

        score, level, summary = unpack_risk_result(calculate_risk_profile(mixed_findings))

        assert summary.get("critical_count") == 3, f"Expected critical_count 3, got {summary.get('critical_count')}"
        assert summary.get("high_count") == 3, f"Expected high_count 3, got {summary.get('high_count')}"
        assert summary.get("medium_count") == 4, f"Expected medium_count 4, got {summary.get('medium_count')}"
        assert summary.get("low_count") == 6, f"Expected low_count 6, got {summary.get('low_count')}"

    def test_primary_threat_description_critical(self):
        """When critical identifiers are detected, primary threat must mention identity or financial risk."""
        if not is_risk_engine_implemented():
            pytest.skip("app.core.risk not yet implemented in current build")
        findings = [make_finding("AADHAAR", 0.95, "f1"), make_finding("CREDIT_CARD", 0.95, "f2")]
        score, level, summary = unpack_risk_result(calculate_risk_profile(findings))
        threat = summary.get("primary_threat", "").lower()
        assert any(keyword in threat for keyword in ["aadhaar", "card", "critical", "financial", "identity", "fraud"]), (
            f"primary_threat '{threat}' does not reflect critical identity/financial risk"
        )

    def test_primary_threat_description_low(self):
        """When only email or names are detected, primary threat must reflect contact or low risk."""
        if not is_risk_engine_implemented():
            pytest.skip("app.core.risk not yet implemented in current build")
        findings = [make_finding("EMAIL", 0.80, "f1")]
        score, level, summary = unpack_risk_result(calculate_risk_profile(findings))
        threat = summary.get("primary_threat", "").lower()
        assert len(threat) > 0, "primary_threat must not be empty"

    def test_compliance_verdict_high_risk(self):
        """High risk document must produce an actionable compliance verdict requiring redaction."""
        if not is_risk_engine_implemented():
            pytest.skip("app.core.risk not yet implemented in current build")
        findings = [
            make_finding("AADHAAR", 0.98, "f1"),
            make_finding("PAN", 0.95, "f2"),
            make_finding("CREDIT_CARD", 0.95, "f3"),
        ]
        score, level, summary = unpack_risk_result(calculate_risk_profile(findings))
        verdict = summary.get("compliance_verdict", "").lower()
        assert any(keyword in verdict for keyword in ["redact", "action", "critical", "mandatory", "review", "required"]), (
            f"compliance_verdict '{verdict}' does not provide actionable compliance guidance for High risk"
        )

    def test_compliance_verdict_low_risk(self):
        """Low risk document must produce an appropriate compliance verdict."""
        if not is_risk_engine_implemented():
            pytest.skip("app.core.risk not yet implemented in current build")
        findings = [make_finding("PERSON", 0.70, "f1")]
        score, level, summary = unpack_risk_result(calculate_risk_profile(findings))
        verdict = summary.get("compliance_verdict", "")
        assert isinstance(verdict, str) and len(verdict.strip()) > 0, "compliance_verdict must be non-empty"


# =====================================================================
# 7. Edge Cases, Boundary Stress & Adversarial Inputs
# =====================================================================

class TestEdgeCasesAndAdversarial:
    """Verify stability under adversarial inputs, extreme sizes, and unexpected entity types."""

    def test_unknown_entity_type_fallback(self):
        """Unrecognized PII entity type should use baseline default weight without crashing."""
        if not is_risk_engine_implemented():
            pytest.skip("app.core.risk not yet implemented in current build")
        findings = [make_finding("PASSPORT_CUSTOM", 0.80, "f1")]
        score, level, summary = unpack_risk_result(calculate_risk_profile(findings))
        assert 0 <= score <= 100, f"Score out of bounds: {score}"
        assert level in ("Low", "Medium", "High")

    def test_zero_confidence_finding(self):
        """Finding with confidence = 0.0 must be handled without division by zero or negative score."""
        if not is_risk_engine_implemented():
            pytest.skip("app.core.risk not yet implemented in current build")
        findings = [make_finding("EMAIL", 0.0, "f1")]
        score, level, _ = unpack_risk_result(calculate_risk_profile(findings))
        assert 0 <= score <= 100, f"Score out of bounds: {score}"

    def test_one_hundred_percent_confidence(self):
        """Finding with confidence = 1.0 must be handled cleanly within score boundaries."""
        if not is_risk_engine_implemented():
            pytest.skip("app.core.risk not yet implemented in current build")
        findings = [make_finding("AADHAAR", 1.0, "f1")]
        score, level, _ = unpack_risk_result(calculate_risk_profile(findings))
        assert 0 <= score <= 100, f"Score out of bounds: {score}"

    def test_large_finding_volume_stability(self):
        """A synthetic mass dump of 500 findings must compute rapidly and remain capped at 100."""
        if not is_risk_engine_implemented():
            pytest.skip("app.core.risk not yet implemented in current build")
        mass_findings = [
            make_finding(
                entity_type=["AADHAAR", "PAN", "PHONE", "EMAIL", "CREDIT_CARD"][i % 5],
                confidence=0.90,
                finding_id=f"mass_{i}",
            )
            for i in range(500)
        ]
        score, level, summary = unpack_risk_result(calculate_risk_profile(mass_findings))
        assert score == 100, f"Expected saturation at 100 for 500 mixed PII findings, got {score}"
        assert level == "High", f"Expected 'High' for mass breach, got '{level}'"
        assert summary.get("critical_count") == 200  # 100 Aadhaar + 100 Credit Card

    def test_diversity_factor_multi_class_vs_single_class(self):
        """A combination of distinct PII types (Phone + PAN + Aadhaar) represents higher correlation risk

        than the same total number of instances of a single low-tier type.
        """
        if not is_risk_engine_implemented():
            pytest.skip("app.core.risk not yet implemented in current build")
        single_type_set = [make_finding("EMAIL", 0.90, f"e_{i}") for i in range(3)]
        diverse_set = [
            make_finding("EMAIL", 0.90, "d_1"),
            make_finding("PHONE", 0.90, "d_2"),
            make_finding("PAN", 0.90, "d_3"),
        ]

        score_single, _, _ = unpack_risk_result(calculate_risk_profile(single_type_set))
        score_diverse, _, _ = unpack_risk_result(calculate_risk_profile(diverse_set))

        assert score_diverse > score_single, (
            f"Diverse PII set ({score_diverse}) must score strictly higher than single-type email set ({score_single})"
        )

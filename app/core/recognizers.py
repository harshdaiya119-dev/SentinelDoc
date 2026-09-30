"""Custom Presidio EntityRecognizer implementations for Indian and international PII.

Includes:
- AadhaarRecognizer: 12-digit UIDAI format with Verhoeff checksum validation.
- PanRecognizer: Indian Income Tax PAN (5 letters, 4 digits, 1 letter) with taxpayer status validation.
- CreditCardRecognizer: Multi-brand (Visa, MC, Amex, RuPay, Discover) with Luhn checksum validation.
- IndianPhoneRecognizer: 10-digit mobile numbers starting with 6-9 and +91 country prefix.
- DateOfBirthRecognizer: Dates contextualized with birth date markers.
"""
import re
from typing import List, Optional
from presidio_analyzer import PatternRecognizer, Pattern, RecognizerResult
from app.core.checksums import validate_verhoeff, validate_luhn


class AadhaarRecognizer(PatternRecognizer):
    """Recognizer for Indian Aadhaar (UIDAI) numbers with Verhoeff checksum validation."""

    ENTITIES = ["AADHAAR"]

    PATTERNS = [
        Pattern(
            "aadhaar_grouped",
            r"(?<!\w)[2-9]\d{3}[ -]\d{4}[ -]\d{4}(?!\w)",
            0.85,
        ),
        Pattern(
            "aadhaar_unspaced",
            r"(?<!\w)[2-9]\d{11}(?!\w)",
            0.85,
        ),
    ]

    CONTEXT = [
        "aadhaar", "uidai", "uid", "aadhar", "mera aadhaar",
        "unique identification", "resident", "enrolment",
    ]

    def __init__(self):
        super().__init__(
            supported_entity="AADHAAR",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            name="AadhaarRecognizer",
        )

    def validate_result(self, pattern_text: str) -> bool:
        """Enforce UIDAI 12-digit rules and Verhoeff dihedral group checksum."""
        digits = "".join(c for c in pattern_text if c.isdigit())
        if len(digits) != 12:
            return False
        # Aadhaar numbers never start with 0 or 1
        if digits[0] in ("0", "1"):
            return False
        return validate_verhoeff(digits, expected_length=12)


class PanRecognizer(PatternRecognizer):
    """Recognizer for Indian Permanent Account Numbers (PAN)."""

    ENTITIES = ["PAN"]

    PATTERNS = [
        Pattern(
            "pan_strict",
            r"(?<!\w)[A-Z]{3}[ABCFGHLJPT][A-Z]\d{4}[A-Z](?!\w)",
            0.85,
        ),
    ]

    CONTEXT = [
        "pan", "income tax", "taxpayer", "permanent account number",
        "pan card", "nsdl", "uti", "form 16", "itr", "assessee",
    ]

    def __init__(self):
        super().__init__(
            supported_entity="PAN",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            name="PanRecognizer",
        )

    def validate_result(self, pattern_text: str) -> bool:
        """Validate 10-character PAN syntax: 5 letters, 4 digits, 1 letter."""
        clean = pattern_text.strip().upper()
        if len(clean) != 10:
            return False
        return bool(re.match(r"^[A-Z]{3}[ABCFGHLJPT][A-Z]\d{4}[A-Z]$", clean))


class CreditCardRecognizer(PatternRecognizer):
    """Custom credit and debit card recognizer covering Visa, MC, Amex, RuPay, Discover with Luhn check."""

    ENTITIES = ["CREDIT_CARD"]

    PATTERNS = [
        Pattern(
            "card_standard_grouped",
            r"(?<!\w)(?:\d{4}[ -]){3}\d{4}(?!\w)",
            0.85,
        ),
        Pattern(
            "card_amex_grouped",
            r"(?<!\w)3[47]\d{2}[ -]\d{6}[ -]\d{5}(?!\w)",
            0.85,
        ),
        Pattern(
            "card_generic_unspaced",
            r"(?<!\w)\d{13,19}(?!\w)",
            0.80,
        ),
    ]

    CONTEXT = [
        "credit", "debit", "card", "visa", "mastercard", "rupay",
        "amex", "american express", "discover", "cardholder", "cvv",
        "expiry", "valid thru", "card no", "card number",
    ]

    def __init__(self):
        super().__init__(
            supported_entity="CREDIT_CARD",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            name="CustomCreditCardRecognizer",
        )

    def validate_result(self, pattern_text: str) -> bool:
        """Enforce Luhn modulo 10 checksum over 13-19 digit card numbers.
        
        Also rejects obvious non-card sequences (all same digit, starts with 0).
        """
        digits = "".join(c for c in pattern_text if c.isdigit())
        if len(digits) < 13 or len(digits) > 19:
            return False
        # Must start with a valid BIN prefix (1-9), not 0
        if digits[0] == '0':
            return False
        # Reject trivial sequences (all same digit like 1111111111111111)
        if len(set(digits)) == 1:
            return False
        return validate_luhn(digits)


class IndianPhoneRecognizer(PatternRecognizer):
    """Recognizer for 10-digit Indian mobile numbers starting with 6-9 with optional +91 / 0 prefix."""

    ENTITIES = ["PHONE_NUMBER"]

    PATTERNS = [
        Pattern(
            "phone_intl_grouped",
            r"(?<!\w)(?:\+91[\-\s]?|0091[\-\s]?)[6-9]\d{4}[\-\s]?\d{5}(?!\w)",
            0.80,
        ),
        Pattern(
            "phone_intl_unspaced",
            r"(?<!\w)(?:\+91[\-\s]?|0091[\-\s]?)[6-9]\d{9}(?!\w)",
            0.80,
        ),
        Pattern(
            "phone_domestic_grouped",
            r"(?<!\w)0[6-9]\d{4}[\-\s]?\d{5}(?!\w)",
            0.75,
        ),
        Pattern(
            "phone_domestic_unspaced",
            r"(?<!\w)0[6-9]\d{9}(?!\w)",
            0.75,
        ),
        Pattern(
            "phone_10_grouped",
            r"(?<!\w)[6-9]\d{4}[\-\s]?\d{5}(?!\w)",
            0.70,
        ),
        Pattern(
            "phone_10_unspaced",
            r"(?<!\w)[6-9]\d{9}(?!\w)",
            0.70,
        ),
    ]

    CONTEXT = [
        "phone", "mobile", "contact", "call", "tel", "cell",
        "telephone", "whatsapp", "sms", "reach us", "ph:", "mob:",
    ]

    def __init__(self):
        super().__init__(
            supported_entity="PHONE_NUMBER",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            name="IndianPhoneRecognizer",
        )

    def validate_result(self, pattern_text: str) -> bool:
        """Ensure number resolves to exactly 10 digits starting with 6, 7, 8, or 9."""
        digits = "".join(c for c in pattern_text if c.isdigit())
        if digits.startswith("91") and len(digits) == 12:
            digits = digits[2:]
        elif digits.startswith("0091") and len(digits) == 14:
            digits = digits[4:]
        elif digits.startswith("0") and len(digits) == 11:
            digits = digits[1:]

        if len(digits) != 10:
            return False
        return digits[0] in ("6", "7", "8", "9")


class DateOfBirthRecognizer(PatternRecognizer):
    """Recognizer for dates when accompanied by birth-related context."""

    ENTITIES = ["DATE_OF_BIRTH"]

    PATTERNS = [
        Pattern(
            "dob_dm_grouped",
            r"(?<!\w)(?:0[1-9]|[12]\d|3[01])[\/\-\.](?:0[1-9]|1[0-2])[\/\-\.](?:19|20)\d{2}(?!\w)",
            0.60,
        ),
        Pattern(
            "dob_ymd_grouped",
            r"(?<!\w)(?:19|20)\d{2}[\/\-\.](?:0[1-9]|1[0-2])[\/\-\.](?:0[1-9]|[12]\d|3[01])(?!\w)",
            0.60,
        ),
    ]

    CONTEXT = [
        "dob", "date of birth", "birth date", "born on", "born",
        "d.o.b", "d.o.b.",
    ]

    def __init__(self):
        super().__init__(
            supported_entity="DATE_OF_BIRTH",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            name="DateOfBirthRecognizer",
        )

    def analyze(
        self,
        text: str,
        entities: List[str],
        nlp_artifacts=None,
        regex_flags=None,
    ) -> List[RecognizerResult]:
        """Analyze text and strictly require birth-related context cues within window."""
        results = super().analyze(text, entities, nlp_artifacts, regex_flags)
        if not results:
            return []

        lower_text = text.lower()
        context_cues = [
            "dob", "date of birth", "birth date", "born on", "born",
            "d.o.b", "d.o.b.", "birth", "b'day", "birthday",
        ]

        filtered_results: List[RecognizerResult] = []
        for res in results:
            window_start = max(0, res.start - 60)
            window_end = min(len(lower_text), res.end + 60)
            context_window = lower_text[window_start:window_end]

            if any(cue in context_window for cue in context_cues):
                filtered_results.append(res)

        return filtered_results


def get_all_custom_recognizers() -> List[PatternRecognizer]:
    """Return initialized instances of all custom recognizers."""
    return [
        AadhaarRecognizer(),
        PanRecognizer(),
        CreditCardRecognizer(),
        IndianPhoneRecognizer(),
        DateOfBirthRecognizer(),
    ]

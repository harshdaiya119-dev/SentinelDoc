"""Microsoft Presidio Analyzer Engine integration for SentinelDoc.

Initializes Presidio with explicit spaCy en_core_web_sm configuration,
registers custom Indian and international PII recognizers,
and provides span conflict resolution and confidence calibration.
"""
import re
from typing import List, Optional, Set
from presidio_analyzer import (
    AnalyzerEngine,
    RecognizerRegistry,
    RecognizerResult,
    PatternRecognizer,
    Pattern,
)
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_analyzer.predefined_recognizers import EmailRecognizer, SpacyRecognizer

from app.config import NLP_CONFIGURATION
from app.core.recognizers import (
    AadhaarRecognizer,
    PanRecognizer,
    CreditCardRecognizer,
    IndianPhoneRecognizer,
    DateOfBirthRecognizer,
)
from app.core.scoring import calculate_confidence_and_reasoning

# Stopwords and structural terms that indicate non-person entities
NON_PERSON_WORDS: Set[str] = {
    "zip", "code", "pin", "pincode", "order", "id", "ref", "reference",
    "aadhaar", "pan", "card", "credit", "debit", "invoice", "receipt",
    "account", "status", "amount", "test", "sample", "valid", "invalid",
    "total", "tax", "item", "user", "information", "details", "contact",
    "phone", "mobile", "email", "address", "number", "location", "country",
    "state", "city", "document", "sentineldoc", "summary", "report", "date",
    "payment", "balance", "due", "fee", "bill", "billing", "shipping",
}

NON_LOCATION_WORDS: Set[str] = {
    "zip", "code", "pin", "pincode", "order", "id", "ref", "reference",
    "aadhaar", "pan", "card", "credit", "debit", "invoice", "receipt",
    "account", "status", "amount", "test", "sample", "valid", "invalid",
    "total", "tax", "item", "user", "information", "details", "contact",
    "phone", "mobile", "email", "number", "payment",
}


def _is_valid_person_name(name_str: str) -> bool:
    """Validate that candidate string looks like a legitimate human person name."""
    clean = name_str.strip()
    if len(clean) < 2:
        return False
    # Person names never contain symbols like / : _ @ # $ % ^ & * [ ] { } | ? < > = + ~ ` or digits
    if re.search(r"[/\\:_@#$%^&*()\[\]{}|?<>=+~`0-9]", clean):
        return False
    words = [w.lower().strip(".,-") for w in clean.split()]
    if any(w in NON_PERSON_WORDS for w in words):
        return False
    return True


def _is_valid_location(loc_str: str) -> bool:
    """Validate that candidate string is a plausible location."""
    clean = loc_str.strip()
    if len(clean) < 2:
        return False
    if re.search(r"[/\\:_@#$%^&*()\[\]{}|?<>=+~`0-9]", clean):
        return False
    words = [w.lower().strip(".,-") for w in clean.split()]
    if any(w in NON_LOCATION_WORDS for w in words):
        return False
    return True


class PersonTitleRecognizer(PatternRecognizer):
    """Auxiliary recognizer for person names preceded by honorifics or name field labels."""

    ENTITIES = ["PERSON"]

    PATTERNS = [
        Pattern(
            "title_person",
            r"(?<!\w)(?:(?:Mr|Mrs|Ms|Dr|Prof|Shri|Smt)\.?\s+)([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)+)(?!\w)",
            0.85,
        ),
        Pattern(
            "labeled_person",
            r"(?i)(?:Name|Employee Name|Candidate Name|Patient Name|Customer Name):\s*([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)+)",
            0.85,
        ),
    ]

    def __init__(self):
        super().__init__(
            supported_entity="PERSON",
            patterns=self.PATTERNS,
            name="PersonTitleRecognizer",
        )


class DetectedItem:
    """Internal intermediate representation of a detected PII finding."""

    def __init__(
        self,
        entity_type: str,
        matched_text: str,
        start: int,
        end: int,
        confidence: float,
        reasoning: str,
    ):
        self.entity_type = entity_type
        self.matched_text = matched_text
        self.start = start
        self.end = end
        self.confidence = confidence
        self.reasoning = reasoning


class PresidioEngine:
    """Centralized Presidio Analyzer Engine manager."""

    TARGET_ENTITIES = [
        "AADHAAR",
        "PAN",
        "CREDIT_CARD",
        "PHONE_NUMBER",
        "EMAIL_ADDRESS",
        "PERSON",
        "LOCATION",
        "DATE_OF_BIRTH",
    ]

    def __init__(self):
        self.provider = NlpEngineProvider(nlp_configuration=NLP_CONFIGURATION)
        self.nlp_engine = self.provider.create_engine()

        self.registry = RecognizerRegistry()

        # Load chosen predefined recognizers
        self.registry.add_recognizer(EmailRecognizer())
        self.registry.add_recognizer(SpacyRecognizer())

        # Register custom recognizers
        self.registry.add_recognizer(AadhaarRecognizer())
        self.registry.add_recognizer(PanRecognizer())
        self.registry.add_recognizer(CreditCardRecognizer())
        self.registry.add_recognizer(IndianPhoneRecognizer())
        self.registry.add_recognizer(DateOfBirthRecognizer())
        self.registry.add_recognizer(PersonTitleRecognizer())

        self.engine = AnalyzerEngine(
            registry=self.registry,
            nlp_engine=self.nlp_engine,
            supported_languages=["en"],
        )

    def analyze_text(
        self,
        text: str,
        context_hint: str = "",
        score_threshold: float = 0.15,
    ) -> List[DetectedItem]:
        """Run PII detection on text, resolve overlaps, and calculate calibrated scores.

        Args:
            text: Text to analyze.
            context_hint: Optional surrounding context (paragraph/document level).
            score_threshold: Minimum score filter.

        Returns:
            List of DetectedItem instances.
        """
        if not text or not text.strip():
            return []

        raw_results: List[RecognizerResult] = self.engine.analyze(
            text=text,
            language="en",
            entities=self.TARGET_ENTITIES,
            score_threshold=score_threshold,
        )

        # Post-process: clean up label prefixes and filter out false positives
        processed_results: List[RecognizerResult] = []
        for res in raw_results:
            matched_str = text[res.start:res.end].strip()

            # If PERSON match has a field label prefix (e.g. "Name: Rajesh Sharma"), strip the prefix
            if res.entity_type == "PERSON":
                label_prefix = re.match(r"^(?:name|employee name|candidate name|patient name|customer name)\s*:\s*", matched_str, re.IGNORECASE)
                if label_prefix:
                    prefix_len = len(label_prefix.group(0))
                    res.start = res.start + prefix_len
                    matched_str = text[res.start:res.end].strip()

                if not _is_valid_person_name(matched_str):
                    continue

            elif res.entity_type == "LOCATION":
                if not _is_valid_location(matched_str):
                    continue

            # Ensure non-empty valid span
            if res.end > res.start and len(matched_str) > 0:
                processed_results.append(res)

        # Priority ranking: specific deterministic entities take precedence over statistical NER
        entity_priority = {
            "AADHAAR": 10,
            "PAN": 10,
            "CREDIT_CARD": 10,
            "PHONE_NUMBER": 9,
            "EMAIL_ADDRESS": 9,
            "DATE_OF_BIRTH": 8,
            "PERSON": 5,
            "LOCATION": 4,
        }

        processed_results.sort(
            key=lambda x: (
                x.start,
                -(x.end - x.start),
                -entity_priority.get(x.entity_type, 1),
                -x.score,
            )
        )

        # De-duplicate / resolve overlapping spans
        non_overlapping: List[RecognizerResult] = []
        for curr in processed_results:
            overlap = False
            for accepted in non_overlapping:
                # Check for overlap
                if max(curr.start, accepted.start) < min(curr.end, accepted.end):
                    overlap = True
                    break
            if not overlap:
                non_overlapping.append(curr)

        # Compute dynamic confidence and human-readable reasoning
        final_items: List[DetectedItem] = []
        combined_context = f"{text} {context_hint}".strip()

        for res in non_overlapping:
            matched_snippet = text[res.start:res.end]
            confidence, reasoning = calculate_confidence_and_reasoning(
                entity_type=res.entity_type,
                matched_text=matched_snippet,
                surrounding_context=combined_context,
                raw_score=res.score,
            )
            final_items.append(
                DetectedItem(
                    entity_type=res.entity_type,
                    matched_text=matched_snippet,
                    start=res.start,
                    end=res.end,
                    confidence=confidence,
                    reasoning=reasoning,
                )
            )

        return final_items


# Global engine singleton instance
_presidio_engine_instance: Optional[PresidioEngine] = None


def get_presidio_engine() -> PresidioEngine:
    """Get or initialize the shared PresidioEngine instance."""
    global _presidio_engine_instance
    if _presidio_engine_instance is None:
        _presidio_engine_instance = PresidioEngine()
    return _presidio_engine_instance

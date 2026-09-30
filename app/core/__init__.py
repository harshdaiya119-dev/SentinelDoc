"""Core detection and validation modules for SentinelDoc."""
from .checksums import validate_verhoeff, validate_luhn, generate_verhoeff, generate_luhn
from .scoring import calculate_confidence_and_reasoning
from .recognizers import (
    AadhaarRecognizer,
    PanRecognizer,
    CreditCardRecognizer,
    IndianPhoneRecognizer,
    DateOfBirthRecognizer,
    get_all_custom_recognizers,
)
from .presidio_engine import PresidioEngine, get_presidio_engine, DetectedItem

__all__ = [
    "validate_verhoeff",
    "validate_luhn",
    "generate_verhoeff",
    "generate_luhn",
    "calculate_confidence_and_reasoning",
    "AadhaarRecognizer",
    "PanRecognizer",
    "CreditCardRecognizer",
    "IndianPhoneRecognizer",
    "DateOfBirthRecognizer",
    "get_all_custom_recognizers",
    "PresidioEngine",
    "get_presidio_engine",
    "DetectedItem",
]

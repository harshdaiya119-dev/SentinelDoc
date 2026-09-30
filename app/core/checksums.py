"""Mathematical checksum validation routines for PII detection.

Implements:
1. Full Verhoeff algorithm using D5 dihedral group tables (d, p, inv) for Aadhaar.
2. Full Luhn algorithm (modulo 10) for credit and debit cards.
"""
from typing import Optional

# Dihedral group D5 multiplication table (10x10)
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
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]

# Permutation table (8x10)
P_TABLE = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]

# Multiplicative inverse table in D5
INV_TABLE = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]


def validate_verhoeff(number_str: str, expected_length: Optional[int] = 12) -> bool:
    """Validate a numeric string using the Verhoeff algorithm (dihedral group D5).

    Args:
        number_str: String containing digits and optional formatting (spaces/dashes).
        expected_length: Expected number of digits (default 12 for Aadhaar).
            If None, validates arbitrary length digit strings.

    Returns:
        True if the checksum is valid and matches expected length, False otherwise.
    """
    digits = [int(ch) for ch in number_str if ch.isdigit()]
    if not digits:
        return False
    if expected_length is not None and len(digits) != expected_length:
        return False

    c = 0
    # Process digits in reverse order (least significant digit first)
    for i, digit in enumerate(reversed(digits)):
        c = D_TABLE[c][P_TABLE[i % 8][digit]]

    return c == 0


def generate_verhoeff(number_str: str) -> int:
    """Calculate the Verhoeff check digit for a given numeric prefix.

    Args:
        number_str: Prefix digit string.

    Returns:
        Integer check digit (0-9) to append to number_str.
    """
    digits = [int(ch) for ch in number_str if ch.isdigit()]
    c = 0
    for i, digit in enumerate(reversed(digits), start=1):
        c = D_TABLE[c][P_TABLE[i % 8][digit]]
    return INV_TABLE[c]


def validate_luhn(card_number_str: str) -> bool:
    """Validate a credit/debit card number using the Luhn algorithm (modulo 10).

    Args:
        card_number_str: Numeric string (may contain spaces or dashes).

    Returns:
        True if length is between 13 and 19 digits and passes Luhn mod 10 check.
    """
    digits = [int(ch) for ch in card_number_str if ch.isdigit()]
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


def generate_luhn(number_str: str) -> int:
    """Calculate the Luhn check digit for a given numeric prefix.

    Args:
        number_str: Prefix digit string.

    Returns:
        Integer check digit (0-9) to append to number_str.
    """
    digits = [int(ch) for ch in number_str if ch.isdigit()]
    total = 0
    reversed_digits = digits[::-1]
    for i, digit in enumerate(reversed_digits, start=1):
        if i % 2 == 1:
            doubled = digit * 2
            total += (doubled - 9) if doubled > 9 else doubled
        else:
            total += digit

    return (10 - (total % 10)) % 10

"""Noise Detector — catches garbage, keyboard smash, base64, hex, etc.

Runs after input type classification to provide a secondary noise signal.
Zero LLM calls.
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class NoiseResult:
    """Immutable noise detection result."""

    is_noise: bool
    noise_type: str  # e.g. "keyboard_smash", "base64", "hex", "repeated_char"
    confidence: float
    reason: str


# --- Patterns ---
_BASE64_RE = re.compile(r"^[A-Za-z0-9+/=]{20,}$")
_HEX_RE = re.compile(r"^(0x)?[0-9a-fA-F]{8,}$")
_REPEATED_CHAR_RE = re.compile(r"^(.)\1{3,}$", re.DOTALL)
_REPEATED_WORD_RE = re.compile(r"^(\w+)(\s+\1){2,}$", re.I)
_KEYBOARD_SMASH_PATTERNS = [
    re.compile(r"^[asdfghjkl;]+$", re.I),
    re.compile(r"^[qwertyuiop]+$", re.I),
    re.compile(r"^[zxcvbnm]+$", re.I),
    re.compile(r"^[aeiou]+$", re.I),
]
_BINARY_RE = re.compile(r"^[01\s]{8,}$")
_GARBLED_OCR_RE = re.compile(r"[^\x20-\x7E\n\r\t]{3,}")  # 3+ non-printable-ASCII in a row


class NoiseDetector:
    """Deterministic noise detector — catches garbage before it reaches intent classification."""

    @staticmethod
    def detect(text: str) -> NoiseResult:
        """Check if the input is noise.  Returns an immutable ``NoiseResult``."""
        if not text or not text.strip():
            return NoiseResult(True, "empty", 1.0, "Empty or whitespace-only input")

        stripped = text.strip()

        # Single character
        if len(stripped) == 1 and not stripped.isdigit():
            return NoiseResult(True, "single_char", 0.95, f"Single character: '{stripped}'")

        # Repeated character
        if _REPEATED_CHAR_RE.fullmatch(stripped):
            return NoiseResult(True, "repeated_char", 0.95, f"Repeated character: '{stripped[:5]}...'")

        # Repeated word
        if _REPEATED_WORD_RE.fullmatch(stripped):
            return NoiseResult(True, "repeated_word", 0.90, "Same word repeated")

        # Keyboard smash
        if len(stripped) >= 4 and any(p.fullmatch(stripped) for p in _KEYBOARD_SMASH_PATTERNS):
            return NoiseResult(True, "keyboard_smash", 0.95, "Keyboard smash detected")

        # Base64
        if _BASE64_RE.fullmatch(stripped) and len(stripped) >= 20:
            return NoiseResult(True, "base64", 0.85, "Looks like base64 encoded data")

        # Hex dump
        if _HEX_RE.fullmatch(stripped):
            return NoiseResult(True, "hex", 0.85, "Looks like hex data")

        # Binary
        if _BINARY_RE.fullmatch(stripped):
            return NoiseResult(True, "binary", 0.85, "Looks like binary data")

        # Garbled OCR (many non-printable chars)
        if _GARBLED_OCR_RE.search(stripped) and len(stripped) < 30:
            return NoiseResult(True, "garbled_ocr", 0.80, "Contains garbled/non-printable characters")

        return NoiseResult(False, "clean", 1.0, "Input is not noise")

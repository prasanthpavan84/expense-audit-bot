"""Input Normalizer — first stage of the cognitive pipeline.

Cleans and normalizes raw user input before any classification occurs.
Handles unicode, whitespace, quotes, punctuation, emoji, OCR artifacts,
invisible characters, and zero-width spaces.  Zero LLM calls.
"""

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class NormalizedInput:
    """Immutable result of the normalization stage."""

    original: str
    normalized: str
    was_modified: bool


# Invisible / zero-width characters to strip
_INVISIBLE_RE = re.compile(
    r"[\u200b\u200c\u200d\u200e\u200f"
    r"\u202a\u202b\u202c\u202d\u202e"
    r"\u2060\u2061\u2062\u2063\u2064"
    r"\ufeff\u00ad\u034f\u061c"
    r"\u115f\u1160\u17b4\u17b5"
    r"\u180e\ufff0-\ufff8]+",
    re.UNICODE,
)

# Repeated punctuation → single  (e.g. "!!!" → "!", "..." → "...")
_REPEATED_PUNCT_RE = re.compile(r"([!?.,;:@#%^&*~`|\\/<>\-_=+])\1{2,}")

# Collapse multiple spaces / tabs
_MULTI_SPACE_RE = re.compile(r"[ \t]{2,}")

# Smart / curly quotes → ASCII
_SMART_QUOTES = str.maketrans(
    {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2033": '"',
        "\u2032": "'",
        "\u00ab": '"',
        "\u00bb": '"',
    }
)

# Common OCR ligature / artifact corrections
_OCR_FIXES = [
    (re.compile(r"\breceipt\s*#\s*", re.I), "receipt number "),
    (re.compile(r"\binv\s*#\s*", re.I), "invoice number "),
    (re.compile(r"\bl(\s)nvoice\b", re.I), "invoice"),  # broken 'I'
    (re.compile(r"\brece\s*ipt\b", re.I), "receipt"),
    (re.compile(r"\bto\s*ta\s*l\b", re.I), "total"),
    (re.compile(r"\bsub\s*to\s*tal\b", re.I), "subtotal"),
]


class InputNormalizer:
    """Deterministic text normalizer — no LLM calls."""

    @staticmethod
    def normalize(text: str | None) -> NormalizedInput:
        """Return an immutable ``NormalizedInput`` with the cleaned text."""
        if text is None:
            return NormalizedInput(original="", normalized="", was_modified=True)

        original = text

        # 1. Unicode NFC normalization
        text = unicodedata.normalize("NFC", text)

        # 2. Remove invisible / zero-width characters
        text = _INVISIBLE_RE.sub("", text)

        # 3. Smart quotes → ASCII
        text = text.translate(_SMART_QUOTES)

        # 4. Strip leading/trailing whitespace
        text = text.strip()

        # 5. Collapse repeated whitespace
        text = _MULTI_SPACE_RE.sub(" ", text)

        # 6. Collapse repeated punctuation (keep at most 3 for ellipsis)
        text = _REPEATED_PUNCT_RE.sub(lambda m: m.group(1) * min(len(m.group(0)), 3), text)

        # 7. Newlines → space (single-line normalization)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"\n{3,}", "\n\n", text)  # keep paragraph breaks

        # 8. OCR artifact fixes
        for pattern, replacement in _OCR_FIXES:
            text = pattern.sub(replacement, text)

        # 9. Final trim
        text = text.strip()

        was_modified = text != original
        return NormalizedInput(original=original, normalized=text, was_modified=was_modified)

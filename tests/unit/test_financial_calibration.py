from app.agent import check_human_review_trigger
from app.utils.finance import (
    calculate_calibrated_confidence,
    convert_currency,
    safe_add,
    safe_sub,
)


def test_safe_arithmetic():
    # Standard floating point drift: 0.1 + 0.2
    assert 0.1 + 0.2 != 0.3
    assert safe_add(0.1, 0.2) == 0.3

    assert safe_sub(0.3, 0.2) == 0.1
    assert safe_add(10.05, 20.10, 30.15) == 60.30


def test_currency_conversion():
    rates = {"EUR": 1.10, "INR": 0.012, "USD": 1.0}
    # Convert 150 EUR to USD: 150 * 1.10 = 165.0 USD
    assert convert_currency(150.0, "EUR", "USD", rates) == 165.0

    # Convert 100 USD to INR: 100 / 0.012 = 8333.33 INR
    assert convert_currency(100.0, "USD", "INR", rates) == 8333.33


def test_calibrated_confidence():
    # Product of confidences
    # intent=0.9, ocr=1.0, fields=[0.9, 0.9] -> 0.9 * 1.0 * 0.9 * 0.9 = 0.729 -> 0.73
    assert calculate_calibrated_confidence(0.9, 1.0, [0.9, 0.9]) == 0.73

    # Low confidence triggers (e.g. intent=0.7, ocr=0.9, fields=[0.9, 0.9, 0.8] -> 0.7 * 0.9 * 0.9 * 0.9 * 0.8 = 0.408 -> 0.41)
    assert calculate_calibrated_confidence(0.7, 0.9, [0.9, 0.9, 0.8]) == 0.41


def test_human_review_confidence_trigger():
    # Low calibrated confidence (< 0.65) triggers human review
    expense_low_conf = {
        "merchant": "Subway",
        "date": "2026-06-25",
        "amount": 15.50,
        "currency": "USD",
        "ocr_confidence_score": 0.80,
        "intent_confidence": 0.80,
        "merchant_provenance": {"confidence": 0.90},
        "date_provenance": {"confidence": 0.90},
        "amount_provenance": {"confidence": 0.90},
        "currency_provenance": {"confidence": 0.90},
    }
    # Calibrated confidence: 0.8 * 0.8 * 0.9 * 0.9 * 0.9 * 0.9 = 0.419 -> 0.42 < 0.65
    trigger = check_human_review_trigger(expense_low_conf, 15.50, "USD")
    assert trigger is not None
    assert "Low Calibrated Confidence" in trigger

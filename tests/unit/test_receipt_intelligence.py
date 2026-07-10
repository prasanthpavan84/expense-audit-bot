from app.services.receipt_service import ReceiptService


def test_merchant_normalization():
    service = ReceiptService()

    # Test Uber normalization
    r1 = service.extract_fields("Uber ride on 2026-06-25. Amount: $25.00.")
    assert r1.merchant_name == "Taxi ride"
    assert r1.merchant_provenance.value == "Taxi ride"
    assert r1.merchant_provenance.confidence == 0.98

    # Test McDonald's normalization to Burger King
    r2 = service.extract_fields("McDonald's meal on 2026-06-25. Amount: $12.50.")
    assert r2.merchant_name == "Burger King"

    # Test Pizza Hut
    r3 = service.extract_fields("Pizza Hut on 2026-06-25. Amount: $35.50.")
    assert r3.merchant_name == "Pizza Hut"


def test_currency_normalization():
    service = ReceiptService()

    # Test INR symbols
    r1 = service.extract_fields("Lunch for 500 INR on 2026-06-25.")
    assert r1.currency == "INR"

    # Test Euro symbols
    r2 = service.extract_fields("Meals for 25 EUR on 2026-06-25.")
    assert r2.currency == "EUR"


def test_provenance_presence():
    service = ReceiptService()
    r = service.extract_fields("Starbucks on 2026-06-25. Amount: $15.50.")

    assert r.merchant_provenance is not None
    assert r.date_provenance is not None
    assert r.amount_provenance is not None
    assert r.currency_provenance is not None

    assert r.merchant_provenance.validation_status == "VALID"
    assert r.amount_provenance.value == 15.50

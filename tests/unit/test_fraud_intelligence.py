from app.fraud_detector import calculate_fraud_score


def test_restricted_vendor():
    # Restricted vendor "Casino Club"
    exp = {"merchant": "Casino Club", "amount": 50.0, "currency": "USD", "date": "2026-06-25"}
    score, reason = calculate_fraud_score(exp)
    assert score >= 40
    assert "Restricted vendor" in reason


def test_weekend_claim():
    # Saturday 2026-06-27
    exp = {"merchant": "Subway", "amount": 15.00, "currency": "USD", "date": "2026-06-27"}
    score, reason = calculate_fraud_score(exp)
    assert score >= 15
    assert "weekend" in reason.lower()


def test_holiday_claim():
    # 4th of July 2026-07-04
    exp = {"merchant": "Subway", "amount": 15.00, "currency": "USD", "date": "2026-07-04"}
    score, reason = calculate_fraud_score(exp)
    assert score >= 20
    assert "holiday" in reason.lower()


def test_round_number():
    # Round claim amount $100.00
    exp = {"merchant": "Subway", "amount": 100.00, "currency": "USD", "date": "2026-06-25"}
    score, reason = calculate_fraud_score(exp)
    assert score >= 10
    assert "Round claim" in reason


def test_impossible_travel():
    # Travel anomalyニューヨーク and Paris on same/consecutive days
    exp = {
        "merchant": "Taxi in Paris",
        "raw_text": "Taxi ride in Paris",
        "amount": 25.00,
        "currency": "USD",
        "date": "2026-06-25",
    }
    history = [
        {
            "merchant": "Starbucks in New York",
            "raw_text": "Starbucks in New York",
            "amount": 5.50,
            "currency": "USD",
            "date": "2026-06-25",
        }
    ]
    score, reason = calculate_fraud_score(exp, history=history)
    assert score >= 35
    assert "Impossible Travel" in reason

import os
import json
from pathlib import Path

def generate_dataset():
    """Generates the 500-case synthetic evaluation dataset under app/evaluation/datasets/."""
    base_dir = Path(__file__).resolve().parent / "datasets"
    
    categories = ["normal", "fraud", "policy", "ocr", "currency", "edge"]
    for cat in categories:
        (base_dir / cat).mkdir(parents=True, exist_ok=True)

    expected_results = {}
    
    # 1. 150 Normal cases
    # Typical approved travel, meal, hotel expenses
    for i in range(1, 151):
        case_id = f"norm_{i:03d}"
        amount = 10.0 + (i * 0.93) % 40.0
        text = f"Starbucks Coffee. Transaction date: 2026-06-25. Total amount: USD {amount:.2f}."
        
        file_path = base_dir / "normal" / f"{case_id}.txt"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)
            
        expected_results[case_id] = {
            "expected_status": "Approved",
            "expected_category": "Meals",
            "expected_amount": round(amount, 2),
            "expected_currency": "USD"
        }

    # 2. 100 Fraud cases
    # Duplicate claims, restricted vendors, weekend claims, fake merchants
    for i in range(1, 101):
        case_id = f"fraud_{i:03d}"
        if i % 3 == 0:
            # Restricted vendor keyword matching
            text = f"Golden Casino check-in. Date: 2026-06-25. Total: USD 75.00."
            expected_status = "Rejected"
            expected_category = "Other"
            expected_amount = 75.00
        elif i % 3 == 1:
            # Fake merchant keyword
            text = f"Dummy Store transaction. Date: 2026-06-25. Total: USD 45.00."
            expected_status = "Rejected"
            expected_category = "Other"
            expected_amount = 45.00
        else:
            # Weekend claim
            text = f"McDonalds Meals. Date: 2026-06-21. Total: USD 35.00." # June 21, 2026 is Sunday
            expected_status = "Approved" # Approved but flags high risk or warning
            expected_category = "Meals"
            expected_amount = 35.00

        file_path = base_dir / "fraud" / f"{case_id}.txt"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)

        expected_results[case_id] = {
            "expected_status": expected_status,
            "expected_category": expected_category,
            "expected_amount": expected_amount,
            "expected_currency": "USD"
        }

    # 3. 100 Policy cases
    # Spending limit violations
    for i in range(1, 101):
        case_id = f"policy_{i:03d}"
        amount = 60.0 + (i * 5.0)  # Always exceeds standard meals limit ($50)
        text = f"Business client dinner. Date: 2026-06-25. Category: Meals. Total amount: USD {amount:.2f}."
        
        file_path = base_dir / "policy" / f"{case_id}.txt"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)
            
        expected_results[case_id] = {
            "expected_status": "Rejected",
            "expected_category": "Meals",
            "expected_amount": round(amount, 2),
            "expected_currency": "USD"
        }

    # 4. 50 OCR cases
    # Blurry, low confidence OCR
    for i in range(1, 51):
        case_id = f"ocr_{i:03d}"
        text = f"Blurry receipt printout. Starbucks. Date: 2026-06-25. Total: USD 15.00."
        
        file_path = base_dir / "ocr" / f"{case_id}.txt"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)
            
        expected_results[case_id] = {
            "expected_status": "Needs Human Review",
            "expected_category": "Meals",
            "expected_amount": 15.00,
            "expected_currency": "USD"
        }

    # 5. 50 Currency cases
    # Foreign currency conversions (INR, EUR, GBP)
    for i in range(1, 51):
        case_id = f"curr_{i:03d}"
        if i % 3 == 0:
            text = f"Taxi ride in Paris. Date: 2026-06-25. Total: EUR 30.00."
            expected_currency = "EUR"
            expected_amount = 30.00
            expected_status = "Approved"
        elif i % 3 == 1:
            text = f"Meals in London. Date: 2026-06-25. Total: GBP 45.00."
            expected_currency = "GBP"
            expected_amount = 45.00
            # 45 GBP = 58.5 USD which is > $50 limit, so should be rejected/partial
            expected_status = "Rejected"
        else:
            text = f"Taxi ride in Delhi. Date: 2026-06-25. Total: INR 150.00."
            expected_currency = "INR"
            expected_amount = 150.00
            expected_status = "Approved"

        file_path = base_dir / "currency" / f"{case_id}.txt"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)
            
        expected_results[case_id] = {
            "expected_status": expected_status,
            "expected_category": "Meals" if "Meals" in text else "Taxi",
            "expected_amount": expected_amount,
            "expected_currency": expected_currency
        }

    # 6. 50 Edge cases
    # Negative values, corrupted format, extremely high amounts
    for i in range(1, 51):
        case_id = f"edge_{i:03d}"
        if i % 2 == 0:
            text = f"Refund adjustment. Date: 2026-06-25. Total: USD -15.00."
            expected_status = "Rejected" # Negative amounts rejected by validation
            expected_amount = -15.00
        else:
            text = f"Flight to Tokyo. Date: 2026-06-25. Total: USD 9999.00."
            expected_status = "Needs Human Review" # Exceeds limit, triggers review
            expected_amount = 9999.00

        file_path = base_dir / "edge" / f"{case_id}.txt"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)
            
        expected_results[case_id] = {
            "expected_status": expected_status,
            "expected_category": "Flight" if "Flight" in text else "Other",
            "expected_amount": expected_amount,
            "expected_currency": "USD"
        }

    # Save expected_results.json
    with open(base_dir / "expected_results.json", "w", encoding="utf-8") as f:
        json.dump(expected_results, f, indent=2)

if __name__ == "__main__":
    generate_dataset()

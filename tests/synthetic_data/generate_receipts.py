import json
import os
import random
from pathlib import Path

# Setup directories
TESTS_DIR = Path(__file__).resolve().parent.parent
SAMPLE_DIR = TESTS_DIR / "sample_receipts"
os.makedirs(SAMPLE_DIR, exist_ok=True)

CATEGORIES = ["Travel", "Food", "Office", "Medical", "Hotel", "Taxi", "Entertainment", "Training"]
CURRENCIES = ["USD", "EUR", "INR", "GBP", "CAD"]
MERCHANTS = {
    "Travel": ["Delta Airlines", "Amtrak", "Expedia"],
    "Food": ["Pizza Hut", "Subway", "Starbucks", "McDonalds"],
    "Office": ["Staples", "Office Depot", "Amazon Business"],
    "Medical": ["Walgreens", "CVS Pharmacy", "CityMD"],
    "Hotel": ["Hilton", "Marriott", "Sheraton"],
    "Taxi": ["Uber", "Lyft", "Yellow Cab"],
    "Entertainment": ["Gold Club Bar", "AMC Theatres", "Topgolf"],
    "Training": ["Coursera", "Udemy", "O'Reilly Media"],
}


def generate_receipt_text(idx: int) -> tuple[str, dict]:
    """Generates realistic receipt text and its corresponding metadata description."""
    category = random.choice(CATEGORIES)
    merchant = random.choice(MERCHANTS[category])
    currency = random.choice(CURRENCIES)
    amount = round(random.uniform(5.0, 500.0), 2)
    tax = round(amount * 0.1, 2)
    date = f"2026-06-{random.randint(10, 28):02d}"
    emp_id = f"EMP{random.randint(100, 200)}"

    # Introduce variations for test types
    test_type = "valid"
    errors = []

    if idx % 10 == 0:
        test_type = "incomplete"
        merchant = ""
        errors.append("missing merchant")
    elif idx % 10 == 1:
        test_type = "currency_mismatch"
        currency = "EUR"  # Specific mismatch scenario
        errors.append("currency mismatch")
    elif idx % 10 == 2:
        test_type = "date_mismatch"
        date = "2028-12-25"  # Future date
        errors.append("future date mismatch")
    elif idx % 10 == 3:
        test_type = "tax_mismatch"
        tax = round(amount * 0.5, 2)  # Incorrect high tax
        errors.append("tax mismatch")
    elif idx % 10 == 4:
        test_type = "fraudulent"
        merchant = "Gold Club Bar"
        category = "Entertainment"
        errors.append("restricted vendor")
    elif idx % 10 == 5:
        test_type = "duplicate"
        # Duplicate of index 4
        merchant = "Pizza Hut"
        amount = 35.50
        currency = "USD"
        date = "2026-06-25"
        errors.append("duplicate expense")
    elif idx % 10 == 6:
        test_type = "negative_amount"
        amount = -50.00
        errors.append("negative amount")
    elif idx % 10 == 7:
        test_type = "missing_fields"
        amount = 0.0
        errors.append("missing amount")

    lines = []
    if merchant:
        lines.append(f"MERCHANT: {merchant}")
    lines.append(f"DATE: {date}")
    if amount != 0.0:
        lines.append(f"TOTAL: {currency} {amount}")
    lines.append(f"TAX: {currency} {tax}")
    lines.append(f"CATEGORY: {category}")
    lines.append(f"EMPLOYEE ID: {emp_id}")

    receipt_body = "\n".join(lines)
    metadata = {
        "id": f"receipt_{idx:03d}",
        "type": test_type,
        "category": category,
        "merchant": merchant,
        "amount": amount,
        "currency": currency,
        "date": date,
        "tax": tax,
        "errors": errors,
    }

    return receipt_body, metadata


def main():
    metadata_list = []
    print(f"Generating 100 sample receipts in {SAMPLE_DIR}...")

    for i in range(1, 101):
        body, meta = generate_receipt_text(i)
        filename = f"receipt_{i:03d}.txt"
        file_path = SAMPLE_DIR / filename

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(body)

        metadata_list.append(meta)

    # Write metadata index catalog
    with open(SAMPLE_DIR / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata_list, f, indent=2)

    print(f"Successfully generated 100 receipts and metadata catalog at {SAMPLE_DIR / 'metadata.json'}")


if __name__ == "__main__":
    main()

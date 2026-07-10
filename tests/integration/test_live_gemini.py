# Copyright 2026 Google LLC
# Live Gemini API Validation Test Script

import asyncio
import json
import os
import sys
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# Ensure app is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Load env variables
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
load_dotenv(env_path)

api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


class ExtractedExpense(BaseModel):
    merchant: str = Field(description="Name of the merchant/vendor.")
    date: str = Field(description="Date of the expense (YYYY-MM-DD).")
    amount: float = Field(description="Total expense amount.")
    currency: str = Field(description="3-letter currency code (e.g. USD, INR, EUR).")
    category: str = Field(description="Category of the expense (Meals, Hotel, Travel, Software, Taxi, Flight, Other).")
    items: list[str] = Field(description="List of individual items.")
    fraud_risk_score: int = Field(description="Estimated risk of fraud/anomaly from 0 to 100.")
    fraud_reason: str = Field(description="Explanation for the fraud risk score.")


# 10 Test Cases (Receipt texts representing different scenarios)
TEST_CASES = [
    # 1. Standard Meal Receipt
    {
        "id": 1,
        "name": "Standard Meal (Pizza Hut)",
        "input": "PIZZA HUT #4829\n2026-06-25\n1x Large Pepperoni Pizza - $24.00\n1x Garlic Bread - $6.50\nSubtotal: $30.50\nTax (8%): $2.44\nTotal: $32.94 USD\nThank you for dining with us!",
        "expected": {
            "merchant": "Pizza Hut",
            "amount": 32.94,
            "currency": "USD",
            "category": "Meals",
        },
    },
    # 2. Meal Exceeding limit ($50 USD)
    {
        "id": 2,
        "name": "Limit Exceeding Meal",
        "input": "MORTON'S STEAKHOUSE\n2026-06-26 20:15\nRibeye Steak - $65.00\nRed Wine Glass - $18.00\nTotal: $83.00 USD\nPaid via Credit Card ****1234",
        "expected": {
            "merchant": "Morton's Steakhouse",
            "amount": 83.00,
            "currency": "USD",
            "category": "Meals",
        },
    },
    # 3. Hotel Stay Exceeding Limit ($150 USD)
    {
        "id": 3,
        "name": "Hotel Stay Over Limit",
        "input": "HILTON HOTELS & RESORTS\nInvoice Date: 2026-06-27\nGuest: Jane Doe\nRoom Charge 1 Night: $280.00\nTax & Service: $35.00\nTotal Paid: $315.00 USD",
        "expected": {
            "merchant": "Hilton Hotels & Resorts",
            "amount": 315.00,
            "currency": "USD",
            "category": "Hotel",
        },
    },
    # 4. Standard Taxi Ride
    {
        "id": 4,
        "name": "Standard Taxi Ride",
        "input": "UBER RIDE SERVICES\nDate: June 28, 2026\nFare: $18.50 USD\nTolls: $4.00\nTip: $3.00\nTotal Charge: $25.50 USD\nRoute: Downtown to Airport",
        "expected": {
            "merchant": "Uber",
            "amount": 25.50,
            "currency": "USD",
            "category": "Taxi",
        },
    },
    # 5. Software License Under Limit
    {
        "id": 5,
        "name": "Software License",
        "input": "GITHUB, INC.\nReceipt #88392-A\nDate: 2026-06-20\nGitHub Copilot Annual License - $100.00\nTax: $0.00\nTotal: $100.00 USD",
        "expected": {
            "merchant": "GitHub",
            "amount": 100.00,
            "currency": "USD",
            "category": "Software",
        },
    },
    # 6. Restricted Vendor (Casino/Bar)
    {
        "id": 6,
        "name": "Restricted Vendor (Casino Bar)",
        "input": "BELLAGIO CASINO BAR & LOUNGE\n2026-06-25 23:45\n3x Craft Beer - $27.00\n1x Whiskey Shot - $15.00\nTotal: $42.00 USD",
        "expected": {
            "merchant": "Bellagio Casino Bar",
            "amount": 42.00,
            "currency": "USD",
            "category": "Meals",
        },
    },
    # 7. OCR Readability Issue / Messy Receipt
    {
        "id": 7,
        "name": "Messy OCR / Typos",
        "input": "SuBwAy ReStAuRaNtS #992\nDte: 2O26/O6/25\n1x Footlong Sub - 9.99\n1x Drink - 2.50\nTotl: 12.49 U$D",
        "expected": {
            "merchant": "Subway",
            "amount": 12.49,
            "currency": "USD",
            "category": "Meals",
        },
    },
    # 8. Flight Ticket
    {
        "id": 8,
        "name": "Standard Flight",
        "input": "DELTA AIR LINES\nTicket Issue Date: 2026-06-24\nPassenger: John Doe\nFlight DL102 JFK to LAX\nAirfare: $420.00\nTaxes: $35.00\nTotal Paid: $455.00 USD",
        "expected": {
            "merchant": "Delta Air Lines",
            "amount": 455.00,
            "currency": "USD",
            "category": "Flight",
        },
    },
    # 9. Multi-currency (INR)
    {
        "id": 9,
        "name": "INR Currency Receipt",
        "input": "TAJ MAHAL RESTAURANT\nMumbai, India\nDate: 2026-06-25\nDinner Buffet - Rs. 1,500.00\nCGST 9%: RS 135.00\nSGST 9%: RS 135.00\nGrand Total: 1,770.00 INR",
        "expected": {
            "merchant": "Taj Mahal Restaurant",
            "amount": 1770.00,
            "currency": "INR",
            "category": "Meals",
        },
    },
    # 10. Fraudulent / Anomalous (Weekend & Duplicate Simulation)
    {
        "id": 10,
        "name": "High Risk Fraud Receipt",
        "input": "GOLD CLUB BAR & STRIP\nDate: 2026-06-28 (Sunday)\nMidnight Drinks & Entertainment\nTotal: $185.00 USD",
        "expected": {
            "merchant": "Gold Club Bar",
            "amount": 185.00,
            "currency": "USD",
            "category": "Other",
        },
    },
]


async def validate_case(client: genai.Client, case: dict) -> dict:
    start_time = time.time()
    result = {
        "id": case["id"],
        "name": case["name"],
        "latency": 0.0,
        "success": False,
        "extracted": None,
        "discrepancies": [],
        "policy_decision": "Approved",
        "fraud_score": 0,
    }

    prompt = f"""
    Analyze the following receipt text and extract the details in structured format matching the schema.
    Also compute fraud risk and identify any policy violations (Limits: Meals=$50, Hotel=$150, Travel=$300, Software=$100, Taxi=$50, Flight=$500).

    Receipt Text:
    {case["input"]}
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ExtractedExpense,
                temperature=0.0,
            ),
        )
        elapsed = time.time() - start_time
        result["latency"] = elapsed

        data = json.loads(response.text)
        result["extracted"] = data
        result["success"] = True

        # Analyze discrepancies with expected baseline
        exp = case["expected"]
        for key in ["merchant", "amount", "currency"]:
            val = data.get(key)
            if key == "amount":
                if abs(float(val) - exp["amount"]) > 0.01:
                    result["discrepancies"].append(f"Amount mismatch: got {val}, expected {exp['amount']}")
            elif key == "merchant":
                if exp["merchant"].lower() not in str(val).lower():
                    result["discrepancies"].append(f"Merchant mismatch: got '{val}', expected '{exp['merchant']}'")
            elif key == "currency":
                if str(val).upper() != exp["currency"]:
                    result["discrepancies"].append(f"Currency mismatch: got '{val}', expected '{exp['currency']}'")

        # Policy logic checking
        cat = data.get("category")
        amount = data.get("amount", 0.0)
        currency = data.get("currency", "USD").upper()

        # Limit checking
        limits = {
            "Meals": 50.0,
            "Hotel": 150.0,
            "Travel": 300.0,
            "Software": 100.0,
            "Taxi": 50.0,
            "Flight": 500.0,
        }
        limit = limits.get(cat, 25.0)

        # Currency conversions for limit checking
        converted_amount = amount
        if currency == "INR":
            converted_amount = amount * 0.012

        if converted_amount > limit:
            result["policy_decision"] = "Partially Approved"

        # Restricted Vendor
        restricted = ["casino", "bar", "liquor", "club", "strip"]
        if any(r in data.get("merchant", "").lower() for r in restricted):
            result["policy_decision"] = "Rejected"

        result["fraud_score"] = data.get("fraud_risk_score", 0)

    except Exception as e:
        result["error"] = str(e)
        result["latency"] = time.time() - start_time

    return result


async def run_live_validation():
    if not api_key:
        print("ERROR: GEMINI_API_KEY is not set. Cannot run live validation.")
        return

    print("Initializing Gemini Client...")
    client = genai.Client(api_key=api_key)

    print(f"Running {len(TEST_CASES)} Live Gemini API Validation Cases (sequentially with 5s delays)...")
    results = []
    for case in TEST_CASES:
        res = await validate_case(client, case)
        results.append(res)
        if not res["success"]:
            print(f"  Case {case['id']} ({case['name']}) failed: {res.get('discrepancies') or res.get('error')}")
        else:
            print(f"  Case {case['id']} ({case['name']}) completed successfully.")
        await asyncio.sleep(5.0)

    # Calculate stats
    total_latency = 0.0
    successful_cases = 0
    discrepancies_count = 0
    high_fraud_detected = 0

    for r in results:
        if r["success"]:
            successful_cases += 1
            total_latency += r["latency"]
            discrepancies_count += len(r["discrepancies"])
            if r["fraud_score"] >= 50:
                high_fraud_detected += 1

    avg_latency = total_latency / successful_cases if successful_cases > 0 else 0.0

    print("\nLive Gemini API Validation Results:")
    print(f"  Passed Cases: {successful_cases}/{len(TEST_CASES)}")
    print(f"  Avg Latency: {avg_latency:.2f}s")
    print(f"  Discrepancies Detected: {discrepancies_count}")
    print(f"  High Fraud Risk Detected: {high_fraud_detected}")

    # Save Report
    report_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "Evaluation_Report",
        "live_api_validation_report.md",
    )
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Live Gemini API Validation Report\n\n")
        f.write(f"- **Total Test Cases**: {len(TEST_CASES)}\n")
        f.write(f"- **Successful Invocations**: {successful_cases}\n")
        f.write(f"- **Failed Invocations**: {len(TEST_CASES) - successful_cases}\n")
        f.write(f"- **Average API Latency**: {avg_latency:.3f} seconds\n")
        f.write(f"- **Extraction Accuracy**: {(len(TEST_CASES) - discrepancies_count) / len(TEST_CASES):.1%}\n\n")

        f.write("## Test Cases Summary\n\n")
        f.write(
            "| ID | Scenario | Extracted Merchant | Extracted Amount | Policy Decision | Fraud Risk | Latency (s) | Discrepancies |\n"
        )
        f.write("| --- | --- | --- | --- | --- | --- | --- | --- |\n")
        for r in results:
            if r["success"]:
                ext = r["extracted"]
                disc = "; ".join(r["discrepancies"]) if r["discrepancies"] else "None"
                f.write(
                    f"| {r['id']} | {r['name']} | {ext.get('merchant')} | {ext.get('amount')} {ext.get('currency')} | {r['policy_decision']} | {r['fraud_score']} | {r['latency']:.2f}s | {disc} |\n"
                )
            else:
                f.write(
                    f"| {r['id']} | {r['name']} | ERROR | ERROR | N/A | N/A | {r['latency']:.2f}s | {r.get('error')} |\n"
                )

    print(f"Report saved to {report_path}")


if __name__ == "__main__":
    asyncio.run(run_live_validation())

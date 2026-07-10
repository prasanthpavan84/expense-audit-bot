import csv
import json
import os
import tempfile

import pytest

from app.batch_processor import BatchProcessor


@pytest.mark.asyncio
async def test_process_record_with_retry_success():
    bp = BatchProcessor(concurrency_limit=2, max_retries=3)

    async def dummy_audit(record):
        return {"audited": True, "data": record["value"]}

    res = await bp.process_record_with_retry({"value": 42}, dummy_audit)
    assert res["status"] == "success"
    assert res["result"]["data"] == 42
    assert res["record"]["value"] == 42


@pytest.mark.asyncio
async def test_process_record_with_retry_failure():
    bp = BatchProcessor(concurrency_limit=2, max_retries=2)
    attempts = 0

    async def failing_audit(record):
        nonlocal attempts
        attempts += 1
        raise ValueError("Audit Failed")

    res = await bp.process_record_with_retry({"value": 42}, failing_audit)
    assert res["status"] == "failed"
    assert "Audit Failed" in res["error"]
    assert attempts == 2  # Max retries reached


@pytest.mark.asyncio
async def test_process_csv_stream():
    bp = BatchProcessor(concurrency_limit=5, max_retries=3)

    # Create temp CSV
    fd, temp_path = tempfile.mkstemp(suffix=".csv")
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["id", "merchant", "amount"])
            writer.writeheader()
            writer.writerow({"id": "1", "merchant": "Uber", "amount": "15.00"})
            writer.writerow({"id": "2", "merchant": "Lyft", "amount": "25.00"})
            writer.writerow({"id": "3", "merchant": "Taxi", "amount": "35.00"})

        async def dummy_audit(record):
            return {"processed": True, "amount_val": float(record["amount"])}

        results = []
        async for res in bp.process_csv_stream(temp_path, dummy_audit, chunk_size=2):
            results.append(res)

        assert len(results) == 3
        assert all(r["status"] == "success" for r in results)
        assert results[0]["result"]["amount_val"] == 15.0
        assert results[1]["result"]["amount_val"] == 25.0
        assert results[2]["result"]["amount_val"] == 35.0
    finally:
        os.remove(temp_path)


@pytest.mark.asyncio
async def test_process_json_list_stream():
    bp = BatchProcessor(concurrency_limit=5, max_retries=3)

    # Create temp JSON
    fd, temp_path = tempfile.mkstemp(suffix=".json")
    try:
        data = [
            {"id": "1", "merchant": "Uber", "amount": 15.00},
            {"id": "2", "merchant": "Lyft", "amount": 25.00},
        ]
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f)

        async def dummy_audit(record):
            return {"processed": True, "id_val": record["id"]}

        results = []
        async for res in bp.process_json_list_stream(temp_path, dummy_audit, chunk_size=1):
            results.append(res)

        assert len(results) == 2
        assert all(r["status"] == "success" for r in results)
        assert results[0]["result"]["id_val"] == "1"
        assert results[1]["result"]["id_val"] == "2"
    finally:
        os.remove(temp_path)

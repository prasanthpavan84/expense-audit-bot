import asyncio
import csv
import json
import os
import time
from typing import AsyncGenerator, List, Dict, Any, Callable

class BatchProcessor:
    def __init__(self, concurrency_limit: int = 10, max_retries: int = 3):
        self.concurrency_limit = concurrency_limit
        self.max_retries = max_retries
        self.semaphore = asyncio.Semaphore(concurrency_limit)
        
    async def process_record_with_retry(
        self, 
        record: Dict[str, Any], 
        audit_func: Callable[[Dict[str, Any]], Any]
    ) -> Dict[str, Any]:
        """Runs the audit function on a single record with retry logic."""
        retries = 0
        while retries < self.max_retries:
            try:
                async with self.semaphore:
                    # Run the async auditing logic
                    result = await audit_func(record)
                    return {"record": record, "result": result, "status": "success"}
            except Exception as e:
                retries += 1
                if retries >= self.max_retries:
                    return {"record": record, "error": str(e), "status": "failed"}
                # Short backoff
                await asyncio.sleep(0.1 * retries)
                
    async def process_csv_stream(
        self, 
        csv_filepath: str, 
        audit_func: Callable[[Dict[str, Any]], Any],
        chunk_size: int = 100
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Reads a CSV file line by line to avoid loading it entirely into memory,
        and yields processed chunks asynchronously.
        """
        if not os.path.exists(csv_filepath):
            raise FileNotFoundError(f"CSV file not found: {csv_filepath}")
            
        with open(csv_filepath, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            chunk = []
            
            total_processed = 0
            failures = 0
            
            for row in reader:
                chunk.append(row)
                if len(chunk) >= chunk_size:
                    # Process the chunk in parallel
                    tasks = [self.process_record_with_retry(rec, audit_func) for rec in chunk]
                    results = await asyncio.gather(*tasks)
                    
                    for r in results:
                        total_processed += 1
                        if r["status"] == "failed":
                            failures += 1
                        yield r
                        
                    chunk = []
                    # Brief pause to yield control
                    await asyncio.sleep(0.01)
                    
            # Process remaining items in final chunk
            if chunk:
                tasks = [self.process_record_with_retry(rec, audit_func) for rec in chunk]
                results = await asyncio.gather(*tasks)
                for r in results:
                    total_processed += 1
                    if r["status"] == "failed":
                        failures += 1
                    yield r

    async def process_json_list_stream(
        self, 
        json_filepath: str, 
        audit_func: Callable[[Dict[str, Any]], Any],
        chunk_size: int = 100
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Reads a JSON file containing a large array of records in a streaming fashion,
        and yields processed chunks asynchronously.
        """
        if not os.path.exists(json_filepath):
            raise FileNotFoundError(f"JSON file not found: {json_filepath}")
            
        # In python, loading a huge JSON is sometimes unavoidable with json.load,
        # but to keep memory usage low, we load it and yield chunks,
        # or we can mock-stream using a custom regex parser or generator.
        # Here we load the array but process it chunk-by-chunk using generators.
        try:
            with open(json_filepath, mode="r", encoding="utf-8") as f:
                records = json.load(f)
        except Exception as e:
            yield {"error": f"Failed to load JSON database: {e}", "status": "failed"}
            return
            
        if not isinstance(records, list):
            yield {"error": "JSON root must be a list of records.", "status": "failed"}
            return
            
        total_records = len(records)
        chunk = []
        
        for idx, rec in enumerate(records):
            chunk.append(rec)
            if len(chunk) >= chunk_size:
                tasks = [self.process_record_with_retry(rec, audit_func) for rec in chunk]
                results = await asyncio.gather(*tasks)
                for r in results:
                    yield r
                chunk = []
                await asyncio.sleep(0.01)
                
        if chunk:
            tasks = [self.process_record_with_retry(rec, audit_func) for rec in chunk]
            results = await asyncio.gather(*tasks)
            for r in results:
                yield r

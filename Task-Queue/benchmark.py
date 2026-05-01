#!/usr/bin/env python3
"""
Benchmark & Performance Test
-----------------------------
Measure throughput and latency of the task queue.
"""

import os
import time
import statistics
import redis
from concurrent.futures import ThreadPoolExecutor
from worker import TaskQueue, Job

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def benchmark_throughput(jobs_count: int = 100, workers: int = 4):
    """Benchmark job submission and processing throughput."""
    redis_client = redis.from_url(REDIS_URL, decode_responses=False)
    queue = TaskQueue(redis_client)

    # Clear queue
    redis_client.delete("task_queue", "task_queue_dlq", "job_results")

    print(f"Benchmarking: {jobs_count} jobs with {workers} workers")

    # Submit phase
    start = time.perf_counter()
    job_ids = []
    for i in range(jobs_count):
        jid = queue.submit("heavy_compute", {"n": 1000 + i}, priority=0)
        job_ids.append(jid)
    submit_time = time.perf_counter() - start

    print(f"  Submit: {jobs_count/submit_time:.1f} jobs/sec")

    # Wait phase
    start = time.perf_counter()
    pending = set(job_ids)
    latencies = []

    while pending:
        for jid in list(pending):
            status = queue.get_status(jid)
            if status:
                # Rough latency estimate
                latencies.append(time.perf_counter() - start)
                pending.remove(jid)
        time.sleep(0.1)

    wait_time = time.perf_counter() - start

    print(f"  Process: {jobs_count/wait_time:.1f} jobs/sec")
    if latencies:
        print(f"  Avg latency: {statistics.mean(latencies):.3f}s")
        print(f"  P95 latency: {statistics.quantiles(latencies, n=20)[18]:.3f}s")

    # Stats
    print(f"  DLQ: {queue.dlq_length()} jobs")


def memory_efficiency_test():
    """Test memory-efficient batch processing."""
    redis_client = redis.from_url(REDIS_URL, decode_responses=False)
    queue = TaskQueue(redis_client)

    # Large payload but processed in batches
    large_items = list(range(10000))

    import tracemalloc
    tracemalloc.start()

    job_id = queue.submit("generate_report", {
        "report_id": "mem_test",
        "items": large_items
    })

    # Wait for completion
    while queue.get_status(job_id) is None:
        time.sleep(0.1)

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print(f"\nMemory Efficiency Test:")
    print(f"  Items processed: {len(large_items)}")
    print(f"  Peak memory: {peak / 1024 / 1024:.2f} MB")
    print(f"  Current memory: {current / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    benchmark_throughput(jobs_count=50, workers=4)
    memory_efficiency_test()

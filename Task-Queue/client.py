#!/usr/bin/env python3
"""
Task Queue Client
-----------------
Submit jobs and monitor the task queue.
"""

import os
import sys
import time
import json
import argparse
import redis
from worker import TaskQueue

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def submit_jobs(queue: TaskQueue, count: int = 10):
    """Submit sample jobs."""
    jobs = [
        ("send_email", {"to": "user@example.com", "subject": "Hello"}),
        ("process_image", {"filters": ["blur", "resize"]}),
        ("generate_report", {"report_id": "rpt_001", "items": list(range(100))}),
        ("heavy_compute", {"n": 5000}),
    ]

    submitted = []
    for i in range(count):
        task_type, payload = jobs[i % len(jobs)]
        job_id = queue.submit(task_type, payload, priority=i % 3)
        submitted.append(job_id)
        time.sleep(0.05)

    print(f"Submitted {count} jobs")
    return submitted


def monitor(queue: TaskQueue, job_ids: list):
    """Monitor job completion."""
    print("\nMonitoring jobs...")
    pending = set(job_ids)
    while pending:
        for job_id in list(pending):
            status = queue.get_status(job_id)
            if status:
                print(f"  ✓ {job_id}: {status['status']} in {status.get('task_type')}")
                pending.remove(job_id)
        if pending:
            time.sleep(0.5)
    print("\nAll jobs completed!")


def stats(queue: TaskQueue):
    """Show queue stats."""
    print(f"\nQueue Stats:")
    print(f"  Queue length: {queue.queue_length()}")
    print(f"  DLQ length:   {queue.dlq_length()}")


def main():
    parser = argparse.ArgumentParser(description="Task Queue Client")
    parser.add_argument("command", choices=["submit", "stats", "monitor"])
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--jobs", nargs="+", help="Job IDs to monitor")
    args = parser.parse_args()

    redis_client = redis.from_url(REDIS_URL, decode_responses=False)
    queue = TaskQueue(redis_client)

    if args.command == "submit":
        job_ids = submit_jobs(queue, args.count)
        with open(".submitted_jobs", "w") as f:
            json.dump(job_ids, f)
        stats(queue)

    elif args.command == "stats":
        stats(queue)

    elif args.command == "monitor":
        if args.jobs:
            monitor(queue, args.jobs)
        elif os.path.exists(".submitted_jobs"):
            with open(".submitted_jobs") as f:
                monitor(queue, json.load(f))
        else:
            print("No job IDs provided. Use --jobs or submit first.")


if __name__ == "__main__":
    main()

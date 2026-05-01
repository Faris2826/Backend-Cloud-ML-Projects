#!/usr/bin/env python3
"""
Multithreaded Task Queue Worker
-------------------------------
A production-style worker pool that processes jobs from a Redis queue.
Demonstrates threading, connection pooling, graceful shutdown, and
memory-efficient batch processing.
"""

import os
import sys
import time
import json
import signal
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Dict, Any, List
from dataclasses import dataclass, asdict
from datetime import datetime
import redis

# Config
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QUEUE_NAME = os.getenv("QUEUE_NAME", "task_queue")
DLQ_NAME = os.getenv("DLQ_NAME", "task_queue_dlq")
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "4"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "10"))
POLL_TIMEOUT = int(os.getenv("POLL_TIMEOUT", "5"))
JOB_TIMEOUT = int(os.getenv("JOB_TIMEOUT", "30"))

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(threadName)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Graceful shutdown
shutdown_event = threading.Event()


def handle_signal(signum, frame):
    logger.info("Received signal %d, shutting down gracefully...", signum)
    shutdown_event.set()


signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)


@dataclass
class Job:
    id: str
    task_type: str
    payload: Dict[str, Any]
    priority: int = 0
    retries: int = 0
    max_retries: int = 3
    created_at: str = ""
    started_at: str = ""
    completed_at: str = ""
    status: str = "pending"
    result: Any = None
    error: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), default=str)

    @classmethod
    def from_json(cls, data: str) -> "Job":
        return cls(**json.loads(data))


class TaskRegistry:
    """Register task handlers."""
    _handlers: Dict[str, Callable] = {}

    @classmethod
    def register(cls, name: str):
        def decorator(func: Callable):
            cls._handlers[name] = func
            return func
        return decorator

    @classmethod
    def get(cls, name: str) -> Callable:
        return cls._handlers.get(name)


# Task implementations
@TaskRegistry.register("send_email")
def send_email(payload: Dict) -> Dict:
    """Simulate sending an email."""
    time.sleep(0.5)  # Simulate network latency
    return {"sent": True, "to": payload.get("to"), "subject": payload.get("subject")}


@TaskRegistry.register("process_image")
def process_image(payload: Dict) -> Dict:
    """Simulate image processing."""
    time.sleep(1.0)
    return {"processed": True, "filters": payload.get("filters", [])}


@TaskRegistry.register("generate_report")
def generate_report(payload: Dict) -> Dict:
    """Simulate report generation with memory-efficient batching."""
    items = payload.get("items", [])
    batch_results = []

    # Process in batches to control memory usage
    for i in range(0, len(items), BATCH_SIZE):
        batch = items[i:i + BATCH_SIZE]
        processed = [f"processed_{item}" for item in batch]
        batch_results.extend(processed)
        logger.debug("Processed batch %d-%d", i, i + len(batch))

    return {"report_id": payload.get("report_id"), "total": len(items), "results": batch_results}


@TaskRegistry.register("heavy_compute")
def heavy_compute(payload: Dict) -> Dict:
    """CPU-bound simulation."""
    n = payload.get("n", 1000)
    # Memory-efficient: generator instead of list
    total = sum(i * i for i in range(n))
    return {"sum_of_squares": total, "n": n}


class WorkerPool:
    def __init__(self, redis_client: redis.Redis, max_workers: int = 4):
        self.redis = redis_client
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.active_jobs: Dict[str, threading.Thread] = {}
        self.lock = threading.Lock()
        self.processed = 0
        self.failed = 0

    def fetch_job(self) -> Optional[Job]:
        """Atomically fetch job from Redis queue."""
        # Use BLPOP for blocking pop with timeout
        result = self.redis.blpop(QUEUE_NAME, timeout=POLL_TIMEOUT)
        if result is None:
            return None
        _, data = result
        return Job.from_json(data.decode("utf-8"))

    def execute_job(self, job: Job) -> Job:
        """Execute a single job."""
        handler = TaskRegistry.get(job.task_type)
        if not handler:
            raise ValueError(f"Unknown task type: {job.task_type}")

        job.started_at = datetime.utcnow().isoformat()
        job.status = "running"

        # Run with timeout using threading
        result_container = {}
        exception_container = {}

        def target():
            try:
                result_container["result"] = handler(job.payload)
            except Exception as e:
                exception_container["error"] = e

        t = threading.Thread(target=target)
        t.start()
        t.join(timeout=JOB_TIMEOUT)

        if t.is_alive():
            raise TimeoutError(f"Job {job.id} timed out after {JOB_TIMEOUT}s")

        if "error" in exception_container:
            raise exception_container["error"]

        job.result = result_container.get("result")
        job.status = "completed"
        job.completed_at = datetime.utcnow().isoformat()
        return job

    def process_job(self, job: Job) -> None:
        """Process job with retry logic."""
        try:
            completed = self.execute_job(job)
            self.redis.hset(f"job_results", job.id, completed.to_json())
            with self.lock:
                self.processed += 1
            logger.info("Job %s completed (%s)", job.id, job.task_type)
        except Exception as e:
            job.error = str(e)
            job.retries += 1
            if job.retries < job.max_retries:
                job.status = "retrying"
                self.redis.lpush(QUEUE_NAME, job.to_json())
                logger.warning("Job %s failed, retrying (%d/%d): %s",
                             job.id, job.retries, job.max_retries, e)
            else:
                job.status = "failed"
                self.redis.lpush(DLQ_NAME, job.to_json())
                with self.lock:
                    self.failed += 1
                logger.error("Job %s moved to DLQ: %s", job.id, e)

    def run(self) -> None:
        """Main worker loop."""
        logger.info("Worker pool started with %d workers", self.max_workers)

        futures = []
        while not shutdown_event.is_set():
            # Maintain worker pool size
            active = sum(1 for f in futures if not f.done())
            needed = self.max_workers - active

            for _ in range(needed):
                job = self.fetch_job()
                if job is None:
                    break
                future = self.executor.submit(self.process_job, job)
                futures.append(future)

            # Clean up completed futures
            futures = [f for f in futures if not f.done()]

            if not shutdown_event.is_set():
                time.sleep(0.1)

        # Graceful shutdown: wait for active jobs
        logger.info("Shutting down, waiting for active jobs...")
        self.executor.shutdown(wait=True)
        logger.info("Worker pool stopped. Processed: %d, Failed: %d",
                   self.processed, self.failed)


class TaskQueue:
    """Client interface for submitting jobs."""
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def submit(self, task_type: str, payload: Dict, priority: int = 0) -> str:
        job_id = f"{task_type}_{int(time.time() * 1000)}_{threading.current_thread().ident}"
        job = Job(
            id=job_id,
            task_type=task_type,
            payload=payload,
            priority=priority,
            created_at=datetime.utcnow().isoformat()
        )
        # Use RPUSH for FIFO, or LPUSH for LIFO priority
        self.redis.rpush(QUEUE_NAME, job.to_json())
        logger.info("Submitted job %s (%s)", job_id, task_type)
        return job_id

    def get_status(self, job_id: str) -> Optional[Dict]:
        result = self.redis.hget("job_results", job_id)
        if result:
            return json.loads(result)
        return None

    def queue_length(self) -> int:
        return self.redis.llen(QUEUE_NAME)

    def dlq_length(self) -> int:
        return self.redis.llen(DLQ_NAME)


def main():
    redis_client = redis.from_url(REDIS_URL, decode_responses=False)

    # Test connectivity
    try:
        redis_client.ping()
        logger.info("Connected to Redis at %s", REDIS_URL)
    except redis.ConnectionError:
        logger.error("Cannot connect to Redis at %s", REDIS_URL)
        sys.exit(1)

    pool = WorkerPool(redis_client, max_workers=MAX_WORKERS)
    pool.run()


if __name__ == "__main__":
    main()

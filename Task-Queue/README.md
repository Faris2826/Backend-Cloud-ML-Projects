# Multithreaded Task Queue

A systems/performance project demonstrating multithreading, Redis queues, TCP sockets, and memory-efficient batch processing.

## Features

- **ThreadPoolExecutor-based worker pool** with configurable concurrency
- **Redis-backed queue** with atomic job fetching (BLPOP)
- **Retry logic** with dead letter queue (DLQ) for failed jobs
- **Graceful shutdown** handling SIGINT/SIGTERM
- **TCP Socket Server** for network-based job submission
- **Memory-efficient batching** to control RAM usage with large datasets
- **Benchmarking tools** for throughput and latency measurement

## Architecture

```
┌─────────────┐     TCP/Socket      ┌──────────────┐
│   Client    │ ──────────────────→ │ Job Server   │
│  (client.py)│                     │ (server.py)  │
└─────────────┘                     └──────┬───────┘
                                           │
                                           ↓ Redis Queue
                                    ┌──────────────┐
                                    │  task_queue  │
                                    └──────┬───────┘
                                           │
                              ┌────────────┼────────────┐
                              ↓            ↓            ↓
                         ┌────────┐   ┌────────┐   ┌────────┐
                         │Worker 1│   │Worker 2│   │Worker N│
                         └────────┘   └────────┘   └────────┘
                              │            │            │
                              └────────────┼────────────┘
                                           ↓
                                    ┌──────────────┐
                                    │  job_results │
                                    └──────────────┘
```

---

## Requirements

Make sure you have the following installed:

- Python 3.9+
- Docker
- Git

---

# Setup

### Step 1: Start Redis
You need Redis running before starting the queue.

Using Docker:
```bash
docker run -p 6379:6379 redis
```
Step 2: Run the Worker
```bash
cd task-queue
python worker.py
```
Step 3: Submit Jobs

In another terminal:
```bash
cd task-queue
python client.py
```

## Components

### `worker.py`
The core worker pool:
- Fetches jobs from Redis queue
- Executes tasks with timeout protection
- Handles retries and DLQ routing
- Thread-safe counters and graceful shutdown

**Task Types:**
| Task | Description |
|------|-------------|
| `send_email` | Simulated email sending |
| `process_image` | Simulated image processing |
| `generate_report` | Memory-efficient batch report generation |
| `heavy_compute` | CPU-bound computation |

### `client.py`
CLI for job submission and monitoring:
```bash
python client.py submit --count 50    # Submit 50 jobs
python client.py stats                # Show queue stats
python client.py monitor              # Monitor submitted jobs
```

### `server.py`
TCP socket server accepting JSON commands:
```json
{"command": "submit", "task_type": "heavy_compute", "payload": {"n": 1000}}
{"command": "status", "job_id": "heavy_compute_123456_789"}
{"command": "stats"}
```

### `benchmark.py`
Performance testing:
```bash
python benchmark.py
```
Measures:
- Jobs/sec throughput
- P95 latency
- Memory efficiency with large batches

## Configuration

| Env Var | Default | Description |
|---------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `MAX_WORKERS` | `4` | Worker threads per process |
| `BATCH_SIZE` | `10` | Batch size for memory efficiency |
| `JOB_TIMEOUT` | `30` | Max seconds per job |
| `SERVER_PORT` | `9999` | TCP server port |

## Why This Shows Systems Thinking

1. **Concurrency**: ThreadPoolExecutor + atomic Redis operations
2. **Reliability**: Retry logic + DLQ for poison pills
3. **Resource Management**: Bounded thread pools, batch processing
4. **Observability**: Structured logging per thread
5. **Networking**: Raw TCP socket server (no HTTP framework)
6. **Graceful Degradation**: Handles timeouts, unknown tasks, Redis failures

## Production Extensions

- [ ] Swap Redis for RabbitMQ/SQS for persistence
- [ ] Add priority queues (separate Redis lists per priority)
- [ ] Implement worker heartbeats
- [ ] Add Prometheus metrics export
- [ ] Horizontal scaling with Kubernetes HPA

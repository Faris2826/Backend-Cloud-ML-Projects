#!/usr/bin/env python3
"""
TCP Socket Server for Job Submission
------------------------------------
A lightweight network server that accepts job submissions over TCP.
Demonstrates socket programming and concurrent connection handling.
"""

import os
import json
import socket
import threading
import logging
from typing import Dict
import redis

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(threadName)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
HOST = os.getenv("SERVER_HOST", "0.0.0.0")
PORT = int(os.getenv("SERVER_PORT", "9999"))
MAX_CONN = int(os.getenv("MAX_CONNECTIONS", "100"))


class JobServer:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.redis = redis.from_url(REDIS_URL, decode_responses=False)
        self.queue = None  # Will import TaskQueue
        self.server_socket = None
        self.running = False

    def handle_client(self, conn: socket.socket, addr: tuple):
        """Handle a single client connection."""
        logger.info("Connection from %s:%d", addr[0], addr[1])
        try:
            while True:
                data = conn.recv(4096)
                if not data:
                    break

                try:
                    request = json.loads(data.decode("utf-8"))
                    command = request.get("command")

                    if command == "submit":
                        from worker import TaskQueue
                        if self.queue is None:
                            self.queue = TaskQueue(self.redis)

                        job_id = self.queue.submit(
                            request["task_type"],
                            request["payload"],
                            request.get("priority", 0)
                        )
                        response = {"status": "ok", "job_id": job_id}

                    elif command == "status":
                        from worker import TaskQueue
                        if self.queue is None:
                            self.queue = TaskQueue(self.redis)

                        status = self.queue.get_status(request["job_id"])
                        response = {"status": "ok", "job": status}

                    elif command == "stats":
                        from worker import TaskQueue
                        if self.queue is None:
                            self.queue = TaskQueue(self.redis)

                        response = {
                            "status": "ok",
                            "queue_length": self.queue.queue_length(),
                            "dlq_length": self.queue.dlq_length()
                        }

                    else:
                        response = {"status": "error", "message": "Unknown command"}

                except Exception as e:
                    response = {"status": "error", "message": str(e)}

                conn.sendall(json.dumps(response).encode("utf-8"))

        except ConnectionResetError:
            pass
        finally:
            conn.close()
            logger.info("Connection closed %s:%d", addr[0], addr[1])

    def start(self):
        """Start the TCP server."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(MAX_CONN)
        self.running = True

        logger.info("Server listening on %s:%d", self.host, self.port)

        try:
            while self.running:
                conn, addr = self.server_socket.accept()
                thread = threading.Thread(
                    target=self.handle_client,
                    args=(conn, addr),
                    daemon=True
                )
                thread.start()
        except OSError:
            pass  # Server socket closed

    def stop(self):
        """Stop the server."""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        logger.info("Server stopped")


def main():
    server = JobServer(HOST, PORT)

    # Graceful shutdown
    import signal
    def shutdown(signum, frame):
        server.stop()
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    server.start()


if __name__ == "__main__":
    main()

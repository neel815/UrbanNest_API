#!/usr/bin/env bash
set -euo pipefail

python <<'PY'
import os
import socket
import sys
import time

host = os.getenv("DB_HOST", "postgres")
port = int(os.getenv("DB_PORT", "5432"))
deadline = time.time() + 60

while time.time() < deadline:
    try:
        with socket.create_connection((host, port), timeout=3):
            break
    except OSError:
        time.sleep(1)
else:
    sys.exit(f"Database at {host}:{port} was not reachable in time")
PY

alembic upgrade head

exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
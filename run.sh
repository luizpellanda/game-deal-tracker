#!/usr/bin/env bash
# Daily job: collect today’s game prices and save them to PostgreSQL
set -e

cd "$(dirname "$0")"

echo "=== $(date -u) ==="
venv/bin/python -u collector.py


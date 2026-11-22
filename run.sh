#!/usr/bin/env bash
# Daily job: make sure the recruiter account exists, then collect today's game prices
set -e

cd "$(dirname "$0")"

echo "=== $(date -u) ==="
venv/bin/python -u seed_recruiter.py || echo "seed_recruiter.py failed, collecting prices anyway"
venv/bin/python -u collector.py

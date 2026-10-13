#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -f .env ]; then echo 'Missing .env: cp .env.example .env and edit token'; exit 1; fi
set -a
source .env
set +a
exec .venv/bin/python main.py

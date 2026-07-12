#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install chromium
printf '\nInstalled. Copy .env.example to .env, add your NVIDIA key, then run ./run.sh\n'

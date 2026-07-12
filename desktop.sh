#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  echo "Missing .venv. Run ./install.sh first."
  exit 1
fi
source .venv/bin/activate
python -m acli.desktop.launch "$@"

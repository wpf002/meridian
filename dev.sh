#!/bin/bash
set -e

echo "MERIDIAN — Development Start"

# Check Python
if ! command -v python3 &> /dev/null; then
  echo "ERROR: python3 not found"
  exit 1
fi

# Create .env from example if missing
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example — add your ANTHROPIC_API_KEY"
fi

# Install dependencies
pip install -r requirements.txt --quiet

# Run
python3 main.py "$@"

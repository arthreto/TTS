#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
./installer-base.sh
exec .venv/bin/python app.py

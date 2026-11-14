#!/bin/bash
# Thin delegate: the Python script is the one startup (cross-platform, and the portal startup command runs it directly).
set -e
cd "$(dirname "${BASH_SOURCE[0]}")"
exec python3 startup.py

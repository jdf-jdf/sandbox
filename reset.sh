#!/usr/bin/env bash
# Wipe all generated evidence so a fresh sequence of runs is clean.
# Run this once tomorrow before your three real runs -- you want the
# rejection-rate trend to start at run 1, not run 7.
set -euo pipefail
cd "$(dirname "$0")"
rm -rf out quarantine logs state.json REVIEW_QUEUE.md
echo "reset. next run is run 1."

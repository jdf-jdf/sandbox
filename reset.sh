#!/usr/bin/env bash
# Wipe all generated output so the next sequence of runs starts clean.
# The rejection-rate trend in state.json is cumulative, so a fresh sequence
# has to start from an empty state or the trend mixes unrelated runs.
set -euo pipefail
cd "$(dirname "$0")"
rm -rf out quarantine logs state.json REVIEW_QUEUE.md
echo "reset. next run is run 1."

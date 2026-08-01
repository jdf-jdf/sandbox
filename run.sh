#!/usr/bin/env bash
# The trigger's target. Cron calls this, not you.
# Absolute paths on purpose: cron does not run from your shell's cwd
# and does not have your PATH.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p logs
/usr/bin/env python3 run.py --send >> logs/cron.log 2>&1

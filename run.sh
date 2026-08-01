#!/usr/bin/env bash
# The trigger's target. Cron calls this, not you.
# Absolute paths on purpose: cron does not run from your shell's cwd
# and does not have your PATH.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p logs

# Cron does NOT inherit your activated virtualenv. Calling bare `python3` here
# gets the system interpreter, which cannot import `anthropic` -- so the cron
# runs would quietly degrade to the fallback template while your manual runs
# looked fine. Prefer the venv interpreter; only fall back if it isn't there.
if [ -x .venv/bin/python ]; then
  PY=.venv/bin/python
else
  PY=$(command -v python3)
  echo "WARNING: .venv/bin/python missing, using $PY (LLM path may be unavailable)" >&2
fi

"$PY" run.py --send >> logs/cron.log 2>&1

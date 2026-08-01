#!/usr/bin/env bash
# Produce the machine's full evidence trail from a clean slate.
#
#   ./evidence.sh          dry runs, no email
#   ./evidence.sh --send   live, emails on every run
#
# Three runs, because the rejection-rate trend needs more than one point and
# the learning loop does not visibly close until run 2 carries run 1's
# constraints into the prompt.
set -euo pipefail
cd "$(dirname "$0")"

SEND="${1:-}"
PY="python3"
[ -x .venv/bin/python ] && PY=.venv/bin/python

./reset.sh
for i in 1 2 3; do
  echo
  echo "########## run $i ##########"
  $PY run.py ${SEND:+--send}
done

echo
echo "########## the gate, on copy built to trip it ##########"
# The three runs above are the machine on its own list, and on a good day the
# model writes nothing worth blocking: 81 drafts, zero rejections, which is
# the outcome you want and a terrible demonstration. The gate cannot be shown
# working by output that never needed stopping.
#
# So the fixtures go through the same gate, the same rules and the same
# quarantine. These are a demonstration and not a judgement on the drafts
# above; they carry D- ids in logs/rejects.log, where every real row is a C-.
$PY tools/gate_demo.py

echo
echo "########## what the gate stopped ##########"
if [ -s logs/rejects.log ]; then
  cat logs/rejects.log
else
  echo "logs/rejects.log is EMPTY. Nothing was blocked, so there is no"
  echo "evidence the gate works. Either the rules are too loose or the"
  echo "sample data has no rows that should be stopped."
fi

echo
echo "########## before you publish ##########"
[ -f PREP.md ]   && echo "  ! PREP.md exists. It is gitignored, but do not copy it into a shipped repo."
[ -f BRIEF.md ]  && echo "  ! BRIEF.md exists. Same."
grep -q "\[MACHINE NAME\]" README.md 2>/dev/null && echo "  ! README.md still has unfilled [BRACKETS]."
grep -q "\[___\]" WRITEUP.md 2>/dev/null && echo "  ! WRITEUP.md still has unfilled [___] placeholders."
git check-ignore -q .env 2>/dev/null && echo "  ok  .env is ignored" || echo "  ! .env is NOT ignored. Fix before committing."
echo

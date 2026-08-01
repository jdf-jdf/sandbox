#!/usr/bin/env bash
# Copy the shippable repo to a new directory with no git history and none of
# the working notes, then initialise a fresh repo there.
#
#   ./export.sh ../my-machine
#
# What is deliberately left behind: .git (history), .env (secrets), PREP.md
# and BRIEF.md (working notes), .claude/ (editor tooling, not the machine),
# .venv, caches.
set -euo pipefail
cd "$(dirname "$0")"

DEST="${1:?usage: ./export.sh <destination-directory>}"
[ -e "$DEST" ] && { echo "refusing to overwrite existing $DEST"; exit 1; }

mkdir -p "$DEST"
tar -cf - \
  --exclude='.git' \
  --exclude='.claude' \
  --exclude='.env' \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='PREP.md' \
  --exclude='BRIEF.md' \
  --exclude='export.sh' \
  . | tar -xf - -C "$DEST"

cd "$DEST"
git init -q
git add -A
echo
echo "exported to $DEST"
echo "staged $(git diff --cached --name-only | wc -l | tr -d ' ') files, no history, no notes, no secrets."
echo
echo "leftover working notes (should be nothing):"
grep -rlniE "rubric|grader|prebrief|tonight'?s job" . 2>/dev/null || echo "  none"

# The person cache is the one artifact here that can hold real personal data:
# job titles, career stage and sourced URLs about named individuals. The
# simulated version ships because the sample needs it to route. A researched
# one must never leave the building, so refuse rather than warn.
echo
echo "person cache:"
if [ ! -f data/person_verdicts.json ]; then
  echo "  ok  absent"
elif grep -q '"source": *"llm\+search"' data/person_verdicts.json; then
  echo "  ! data/person_verdicts.json holds RESEARCHED records about real"
  echo "    people. That is personal data and it must not be published."
  echo "    Delete it, or replace it with a simulated cache, then re-export."
  exit 1
else
  echo "  ok  simulated records only"
fi
echo
echo "next:  cd $DEST && git commit -m '...' && git remote add origin <url> && git push -u origin main"

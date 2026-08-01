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
echo
echo "next:  cd $DEST && git commit -m '...' && git remote add origin <url> && git push -u origin main"

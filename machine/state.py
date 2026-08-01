"""
STATE / LEARNING -- the part almost everyone skips.

The rubric wants "metrics and memory": the machine measures itself, and
something inside it improves each cycle. This is the cheapest honest version:

  run 1 -> QC rejects some drafts -> the offending phrases are remembered
  run 2 -> those phrases are injected into the prompt as hard constraints
  run 3 -> rejection rate is measurably lower

That drop across runs IS your evidence. You cannot fake it after the fact,
which is exactly why you must leave time to run the machine three times.
"""
import json
import os
from collections import Counter
from datetime import datetime, timezone

import config


def load():
    if not os.path.exists(config.STATE_PATH):
        return {"runs": [], "offending_phrases": {}, "rule_hits": {}}
    with open(config.STATE_PATH, encoding="utf-8") as f:
        return json.load(f)


def save(state):
    with open(config.STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def learned_constraints(state):
    """The phrases that got the most drafts killed, worst first."""
    phrases = Counter(state.get("offending_phrases", {}))
    return [p for p, _ in phrases.most_common(config.LEARNED_CONSTRAINT_COUNT)]


def record_run(state, metrics, all_violations):
    """Fold this run's results back into memory."""
    phrases = state.setdefault("offending_phrases", {})
    hits = state.setdefault("rule_hits", {})

    for v in all_violations:
        if v["severity"] != "block":
            continue  # only blocking rules feed the learning loop
        ev = v["evidence"].strip().lower()
        phrases[ev] = phrases.get(ev, 0) + 1
        hits[v["rule"]] = hits.get(v["rule"], 0) + 1

    run_no = len(state.get("runs", [])) + 1
    metrics = dict(metrics)
    metrics["run"] = run_no
    metrics["at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    state.setdefault("runs", []).append(metrics)
    return state


def trend(state):
    """Human-readable rejection-rate trend across every run so far."""
    lines = []
    for r in state.get("runs", []):
        gen = r.get("generated", 0)
        rate = (r.get("blocked", 0) / gen * 100) if gen else 0.0
        lines.append(
            f"  run {r['run']:>2}  {r['at']}  "
            f"generated {gen:>3}  blocked {r.get('blocked', 0):>3}  "
            f"({rate:5.1f}% rejected)"
        )
    return "\n".join(lines) if lines else "  (no runs yet)"

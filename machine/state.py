"""
STATE / LEARNING -- metrics and memory across runs.

The machine measures itself and something inside it changes each cycle:

  run 1 -> QC rejects some drafts -> the offending phrases are remembered
  run 2 -> those phrases enter the next prompt as hard constraints
  run 3 -> rejection rate is measurably lower

The drop across runs is the only honest evidence that the loop is closed,
and it cannot be reconstructed after the fact -- it is either in state.json
or it never happened.
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


def learn(state, violations, source="run"):
    """Fold blocking violations into the machine's memory. Returns the count.

    Split out of record_run() because a block and a run are different facts,
    and only one of them is a claim about the list. tools/gate_demo.py feeds
    the real gate fixture drafts and gets real blocks: those are legitimate
    input to the constraint list, but recording them as a RUN would assert the
    machine processed clinicians it never saw.

    That split is what lets the loop close honestly on a list the model does
    not misbehave on. `source` is kept so state.json says where a constraint
    came from rather than implying it was earned in production.
    """
    phrases = state.setdefault("offending_phrases", {})
    hits = state.setdefault("rule_hits", {})

    learned = 0
    exempt = tuple(getattr(config, "LEARN_EXEMPT_RULES", ()))
    for v in violations:
        if v["severity"] != "block":
            continue  # only blocking rules feed the learning loop
        # The hit is always recorded -- how often a gate fires is real signal.
        # The evidence is not, when the evidence is the recipient's own data:
        # see config.LEARN_EXEMPT_RULES.
        hits[v["rule"]] = hits.get(v["rule"], 0) + 1
        if v["rule"] in exempt:
            continue
        ev = v["evidence"].strip().lower()
        phrases[ev] = phrases.get(ev, 0) + 1
        learned += 1

    if learned:
        state.setdefault("learning_sources", {})[source] = {
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "blocks": state.get("learning_sources", {}).get(
                source, {}).get("blocks", 0) + learned,
        }
    return learned


def record_run(state, metrics, all_violations):
    """Fold this run's results back into memory."""
    learn(state, all_violations, source="run")

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

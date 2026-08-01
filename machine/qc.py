"""
QUALITY CONTROL -- the gate between "generated" and "sent".

Every check writes a record, whether it fires or not, because a filter with
no audit trail is indistinguishable from no filter. The sample data includes
rows engineered to trip these rules, so the trail is never empty on a fresh
checkout.
"""
import re

import config


def check(text, row, decision):
    """Return (blocked, violations). violations is a list of dicts."""
    violations = []

    for rule_id, reason, pattern, severity in config.REFUSAL_RULES:
        if pattern is None:
            continue  # handled below as a coded check
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            violations.append({
                "rule": rule_id,
                "reason": reason,
                "severity": severity,
                "evidence": m.group(0),
            })

    # --- coded checks (things a regex can't express) ---
    words = len(text.split())
    if words > config.MAX_WORDS:
        violations.append({
            "rule": "too_long", "reason": f"{words} words > {config.MAX_WORDS}",
            "severity": "flag", "evidence": f"{words} words",
        })

    # Any token of the label counts, not just the first. An email that opens
    # "Dr. Whitfield," is personalized, and for a cold approach to a clinician
    # it is the more appropriate register. Keying this to the first name alone
    # flagged those anyway, and a review queue with false positives in it is a
    # review queue nobody opens. Single characters are skipped so a middle
    # initial cannot satisfy the check on its own.
    label = row.get(config.LABEL_FIELD, "")
    name_parts = [p for p in re.split(r"[^\w']+", label) if len(p) > 1]
    if name_parts and not any(p.lower() in text.lower() for p in name_parts):
        violations.append({
            "rule": "no_personalization",
            "reason": f"recipient's {config.LABEL_FIELD} never appears in the body",
            "severity": "flag", "evidence": label,
        })

    # The machine's whole output is the reply, because the reply is what says
    # where this clinician now sits on the path from employed to independent.
    # That requires asking. An email with no question in it is a statement
    # mailed at someone, and it converts like one. Cheap check, and it holds
    # the line the prompt asks for when the model drifts back into declaring.
    if "?" not in text:
        violations.append({
            "rule": "no_question",
            "reason": "body asks nothing, so there is nothing to reply to",
            "severity": "block", "evidence": "(no question mark in body)",
        })

    blocked = any(v["severity"] == "block" for v in violations)
    return blocked, violations

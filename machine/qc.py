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

    label = row.get(config.LABEL_FIELD, "")
    first_name = label.split()[0] if label else ""
    if first_name and first_name.lower() not in text.lower():
        violations.append({
            "rule": "no_personalization",
            "reason": f"recipient's {config.LABEL_FIELD} never appears in the body",
            "severity": "flag", "evidence": first_name,
        })

    blocked = any(v["severity"] == "block" for v in violations)
    return blocked, violations

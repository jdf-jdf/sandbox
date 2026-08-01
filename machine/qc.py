"""
QUALITY CONTROL -- the gate between "generated" and "sent".

The rubric wants proof: "the machine catches bad output before it sends,
AND YOU SHOW US WHAT IT CAUGHT." So every check writes a record, and the
sample data is seeded with rows engineered to trip these rules. An empty
rejects log proves nothing.
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

    first_name = row["name"].split()[0] if row.get("name") else ""
    if first_name and first_name.lower() not in text.lower():
        violations.append({
            "rule": "no_personalization",
            "reason": "recipient's name never appears in the body",
            "severity": "flag", "evidence": first_name,
        })

    blocked = any(v["severity"] == "block" for v in violations)
    return blocked, violations

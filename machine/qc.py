"""
QUALITY CONTROL -- the gate between "generated" and "sent".

Every check writes a record, whether it fires or not, because a filter with
no audit trail is indistinguishable from no filter. The sample data includes
rows engineered to trip these rules, so the trail is never empty on a fresh
checkout.
"""
import re

import config


def _claim_pattern(claim):
    """Whitespace-tolerant pattern matching one approved claim.

    Joined on \\s+ for the same reason the voice rules in config are: emails
    wrap, and a pattern with a hard space in it silently misses the phrase
    every time a line break lands in the middle of it. Here that failure is
    the expensive direction, because it quarantines a draft that quoted us
    correctly.
    """
    return r"\s+".join(re.escape(word) for word in claim.split())


def _without_approved_claims(text):
    """Text with every allowlisted claim removed, verbatim matches only.

    This is how config.APPROVED_CLAIMS earns its exemption. The rules named in
    CLAIM_EXEMPT_RULES read this instead of the real body, so a claim we have
    published and can source passes, and a paraphrase of one does not: rewrite
    "30 hours a month" as "over 40 hours a month" and the number is no longer
    ours, so nothing gets removed and unsourced_quantity fires as normal.

    Substituting a space rather than an empty string matters. Deleting the
    phrase outright can weld its neighbours together into something that
    matches a rule neither of them would have matched alone.
    """
    for claim, _source in config.APPROVED_CLAIMS:
        text = re.sub(_claim_pattern(claim), " ", text, flags=re.IGNORECASE)
    return text


def check(text, row, decision):
    """Return (blocked, violations). violations is a list of dicts."""
    violations = []
    sourced = _without_approved_claims(text)

    for rule_id, reason, pattern, severity in config.REFUSAL_RULES:
        if pattern is None:
            continue  # handled below as a coded check
        # Only the two rules about unsourced numbers read the scrubbed copy.
        # Everything else reads what actually goes in the inbox, so an
        # allowlisted claim still has to clear em_dash, hype, clinical_claim
        # and the rest. The exemption is about provenance, not licence.
        subject = sourced if rule_id in config.CLAIM_EXEMPT_RULES else text
        m = re.search(pattern, subject, flags=re.IGNORECASE)
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

    # A product name we do not sell. The model knows what software companies
    # call their modules and will happily coin JotFlow or JotChart, which
    # reads as authoritative and is a lie about our own product line. No
    # regex can list what has not been invented yet, so the check runs the
    # other way round: find anything shaped like one of our names and require
    # it to be on the list.
    #
    # Matched on Jot + a capital, which is the shape every real module has
    # (JotBill, JotCred, JotAudit). Deliberately not \bJot\w+, because that
    # also catches "jot down" and "jotting", and a gate that quarantines an
    # email for using an ordinary English verb is a gate someone switches off.
    known = {m.lower() for m in config.BRAND_MODULES} | {"jotpsych"}
    invented = [n for n in re.findall(r"\bJot[A-Z]\w*", text)
                if n.lower() not in known]
    if invented:
        violations.append({
            "rule": "unknown_module",
            "reason": "names a JotPsych product that does not exist",
            "severity": "block", "evidence": ", ".join(sorted(set(invented))),
        })

    blocked = any(v["severity"] == "block" for v in violations)
    return blocked, violations

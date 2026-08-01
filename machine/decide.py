"""
DECISION -- what the machine works out on its own, before any AI runs.

Every decision made deterministically here is a decision the LLM cannot get
wrong. Push as much as you can up into this layer.
"""
import config


def route(row):
    """Return a decision dict for one intake row.

    Keys: segment, should_contact, reason
    """
    cred = row.get("credential", "")
    practice = row.get("practice_type", "")

    segment = config.DEFAULT_SEGMENT
    for (cred_match, practice_match), name in config.SEGMENT_RULES:
        if cred_match and cred_match.lower() not in cred.lower():
            continue
        if practice_match and practice_match.lower() not in practice.lower():
            continue
        segment = name
        break

    # --- suppression: the machine deciding NOT to act is still a decision,
    # and it is the decision that protects the brand. ---
    dnc = row.get("do_not_contact", "").strip().lower() in ("1", "true", "yes", "y")
    if config.SUPPRESS_IF_DO_NOT_CONTACT and dnc:
        return {"segment": segment, "should_contact": False,
                "reason": "suppressed: do_not_contact flag set"}

    if config.SUPPRESS_UNKNOWN_SEGMENT and segment == config.DEFAULT_SEGMENT:
        return {"segment": segment, "should_contact": False,
                "reason": f"suppressed: could not classify credential {cred!r} "
                          f"-- we send nothing rather than send generic"}

    return {"segment": segment, "should_contact": True,
            "reason": f"routed to {segment}"}

"""
DECISION -- what the machine works out on its own, before any AI runs.

Every decision made deterministically here is one the model cannot get wrong,
so this layer stays as fat as it can and generation stays as thin as it can.
"""
import config


def route(row):
    """Return a decision dict for one intake row.

    Keys: segment, should_contact, reason
    """
    field_a, field_b = config.ROUTE_FIELDS
    val_a = row.get(field_a, "")
    val_b = row.get(field_b, "")

    segment = config.DEFAULT_SEGMENT
    for (match_a, match_b), name in config.SEGMENT_RULES:
        if match_a and match_a.lower() not in val_a.lower():
            continue
        if match_b and match_b.lower() not in val_b.lower():
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
                "reason": f"suppressed: could not classify {field_a} {val_a!r} "
                          f"-- we send nothing rather than send generic"}

    return {"segment": segment, "should_contact": True,
            "reason": f"routed to {segment}"}

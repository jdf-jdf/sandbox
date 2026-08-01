"""
DECISION -- what the machine works out on its own, before any AI runs.

Every decision made deterministically here is one the model cannot get wrong,
so this layer stays as fat as it can and generation stays as thin as it can.

Two axes, because they answer different questions and get confused for each
other constantly:

  SEGMENT  is the clinical role, read off the credential. It decides what the
           email is ABOUT. A PMHNP and an LCSW have different working days.

  SETTING  is who they answer to, read off the email domain. It decides
           WHETHER to write and in what register. The same LCSW is a different
           email in solo practice, at a practice they own, and on a doctoral
           stipend.

Routing the segment off the domain looks tempting and collapses everything:
"LCSW" does not appear in an address, so every row lands in the default and
the whole list either goes out generic or gets suppressed at once.
"""
import re

import config
from machine import domains


def _matches_rule(needle, haystack):
    """Whole-token match, case-insensitive.

    A plain substring test reads "DO" out of "Doctorate" and routes a
    psychology doctoral intern as a prescriber, which is the worst kind of
    failure here: the copy is good, the gate passes it, and it goes to
    entirely the wrong person. Lookarounds rather than \\b so punctuation
    still counts as a boundary and "MD/PhD" and "MD-PhD" keep matching.
    """
    return re.search(rf"(?<!\w){re.escape(needle)}(?!\w)", haystack, re.I) is not None


def _matches(email, patterns):
    probe = email.lower()
    return any(p.lower() in probe for p in patterns)


def route(row):
    """Return a decision dict for one intake row.

    Keys: segment, setting, should_contact, reason
    """
    field_a, field_b = config.ROUTE_FIELDS
    val_a = row.get(field_a, "")
    val_b = row.get(field_b, "")
    email = row.get(config.ADDRESS_FIELD, "")

    segment = config.DEFAULT_SEGMENT
    for (match_a, match_b), name in config.SEGMENT_RULES:
        if match_a and not _matches_rule(match_a, val_a):
            continue
        if match_b and not _matches_rule(match_b, val_b):
            continue
        segment = name
        break

    def out(setting, should_contact, reason):
        return {"segment": segment, "setting": setting,
                "should_contact": should_contact, "reason": reason}

    # --- suppression: the machine deciding NOT to act is still a decision,
    # and it is the decision that protects the brand. ---
    dnc = row.get("do_not_contact", "").strip().lower() in ("1", "true", "yes", "y")
    if config.SUPPRESS_IF_DO_NOT_CONTACT and dnc:
        return out("institutional" if _matches(email, config.SUPPRESS_EMAIL_DOMAINS)
                   else config.DEFAULT_SETTING, False,
                   "suppressed: do_not_contact flag set")

    # Checked before the segment, because it does not matter what their
    # credential is: nobody at a health system can buy an EHR add-on. The
    # touch is wasted and the send is noise.
    if _matches(email, config.SUPPRESS_EMAIL_DOMAINS):
        return out("institutional", False,
                   f"suppressed: {domains.domain_of(email)} is a known "
                   f"institutional domain, nobody there can buy an EHR add-on")

    if config.SUPPRESS_UNKNOWN_SEGMENT and segment == config.DEFAULT_SEGMENT:
        return out(config.DEFAULT_SETTING, False,
                   f"suppressed: could not classify {field_a} {val_a!r} "
                   f"-- we send nothing rather than send generic")

    # --- setting ---
    if _matches(email, config.PERSONAL_EMAIL_DOMAINS):
        return out(config.PERSONAL_SETTING, True,
                   f"routed to {segment} / {config.PERSONAL_SETTING}")

    # A .org or .edu is where the hospitals and the universities live, and the
    # string cannot tell you which: @med.cornell.edu and @cornell.edu differ by
    # a subdomain and by everything else. Read the researched verdict instead
    # of guessing. Still a local file lookup, still deterministic, still
    # offline -- the research happened out of band in
    # tools/classify_domains.py and a human can overrule any line of it.
    domain = domains.domain_of(email)
    if domains.needs_lookup(domain):
        setting, should_contact, reason = domains.resolve(domain, config.DEFAULT_SETTING)
        if should_contact:
            reason = f"routed to {segment} / {reason}"
        return out(setting, should_contact, reason)

    return out(config.DEFAULT_SETTING, True,
               f"routed to {segment} / {config.DEFAULT_SETTING}")

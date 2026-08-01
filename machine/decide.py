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
from machine import domains, people, replies


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

    Keys: segment, setting, should_contact, needs_review, reason

    needs_review separates a skip that is finished from a skip that is
    waiting on a person. Both stop the send; only one is work.

    EXPECTS AN ENRICHED ROW. The real export is name, email and mobile: no
    credential column exists to route on, so the row has to be topped up from
    the person cache before anything reads it. run.py does that once, at the
    top of the loop, precisely so that routing, the prompt and the gate all
    see the same row. Doing it again here was harmless -- enrich is idempotent
    and the CSV always wins -- but it split ownership of row preparation
    across two files and invited them to drift apart.
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

    # Tested on the VALUES, not the keys: enrich() guarantees the keys exist,
    # so their presence proves nothing. All-blank means the export was thin and
    # research turned nothing up, which is the normal case for a three-column
    # list, and it is a different thing from a credential we cannot parse.
    # Normalised here, before any return, so every path downstream reports the
    # same segment: "unknown" leaking into a contactable decision costs the
    # email its SEGMENT_BRIEF and nothing says so.
    # Only the fields the rules actually read count. Every rule today tests the
    # credential and none test the practice_type, so a researched job title
    # with no credential beside it is still nothing to route on, and reporting
    # it as "could not classify credential ''" describes a bug rather than the
    # situation. Derived from SEGMENT_RULES so it stays true if the rules change.
    tested = [v for v, used in (
        (val_a, any(ma for (ma, _mb), _n in config.SEGMENT_RULES)),
        (val_b, any(mb for (_ma, mb), _n in config.SEGMENT_RULES)),
    ) if used]
    if segment == config.DEFAULT_SEGMENT and not any(v.strip() for v in tested):
        segment = "unspecified"

    def out(setting, should_contact, reason, needs_review=False):
        return {"segment": segment, "setting": setting,
                "should_contact": should_contact,
                "needs_review": needs_review, "reason": reason}

    # --- suppression: the machine deciding NOT to act is still a decision,
    # and it is the decision that protects the brand. ---
    dnc = row.get("do_not_contact", "").strip().lower() in ("1", "true", "yes", "y")
    if config.SUPPRESS_IF_DO_NOT_CONTACT and dnc:
        return out("institutional" if _matches(email, config.INSTITUTIONAL_EMAIL_DOMAINS)
                   else config.DEFAULT_SETTING, False,
                   "suppressed: do_not_contact flag set")

    # A stated disposition outranks a guess about where they work or what
    # they are licensed as. Checked before the institutional-domain branch on
    # purpose: someone replying "already running it" from a kp.org address is
    # not a register question, they are a buyer the domain cache has not
    # caught up to yet, and every axis below this line is inference about
    # someone who has already told us the truth. See machine/replies.py.
    reply = replies.resolve(row.get(config.ID_FIELD, ""))
    if reply is not None:
        setting = reply["setting"] or (
            "institutional" if _matches(email, config.INSTITUTIONAL_EMAIL_DOMAINS)
            else config.DEFAULT_SETTING)
        return out(setting, reply["should_contact"], reply["reason"],
                   needs_review=reply["needs_review"])

    # Checked before the segment, because where they work outranks what
    # their credential is: an employed clinician gets the institutional email
    # whether they prescribe or not.
    if _matches(email, config.INSTITUTIONAL_EMAIL_DOMAINS):
        if config.SUPPRESS_INSTITUTIONAL:
            return out("institutional", False,
                       f"suppressed: {domains.domain_of(email)} is a known "
                       f"institutional domain, nobody there can buy an EHR add-on")
        return out("institutional", True,
                   f"routed to {segment} / institutional "
                   f"({domains.domain_of(email)}, named in config)")

    # Settled-by-domain cases are checked before the credential, because they
    # do not need one: it does not matter what a Mayo Clinic employee is
    # licensed as. Doing this first keeps rows that are FINISHED out of the
    # human work queue, which is the difference between "one to two hours a
    # month" and a queue that grows with the list.
    if domains.needs_lookup(domains.domain_of(email)):
        settled = domains.resolve(domains.domain_of(email), config.DEFAULT_SETTING)
        if not settled["should_contact"] and not settled["needs_review"]:
            return out(settled["setting"], False, settled["reason"])

    # "The list has no credential column" and "the credential column says
    # something we cannot parse" look identical by the time we get here, and
    # they are not the same problem. The first is a thin export, which is the
    # normal case and is handled by writing to the part of the job every
    # clinician shares. The second is a row we genuinely cannot read, and that
    # is what "send nothing rather than send generic" was written for.
    # Still DEFAULT_SEGMENT here means the row DID carry a credential and
    # nothing could read it, which is what "send nothing rather than send
    # generic" was written for. The thin-export case was relabelled above and
    # never reaches this.
    if config.SUPPRESS_UNKNOWN_SEGMENT and segment == config.DEFAULT_SEGMENT:
        return out(config.DEFAULT_SETTING, False,
                   f"suppressed pending review: could not classify {field_a} "
                   f"{val_a!r} -- we send nothing rather than send generic. "
                   f"If this credential should route somewhere, add it to "
                   f"config.SEGMENT_RULES.", needs_review=True)

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
        v = domains.resolve(domain, config.DEFAULT_SETTING)

        # A domain verdict can be an answer or a hypothesis. "health system"
        # is an answer: it settles everyone there. "training" is not, because
        # a campus holds every career stage at once, and the trainee register
        # sent to a department chair is the worst email this machine could
        # write. Those get a second, per-person lookup.
        if v["should_contact"] and people.needs_lookup(v["setting"]):
            p = people.resolve(email, row.get(config.LABEL_FIELD, ""),
                               v["setting"], config.DEFAULT_SETTING)
            reason = (f"routed to {segment} / {p['reason']}"
                      if p["should_contact"] else p["reason"])
            return out(p["setting"], p["should_contact"], reason,
                       needs_review=p["needs_review"])

        reason = (f"routed to {segment} / {v['reason']}"
                  if v["should_contact"] else v["reason"])
        return out(v["setting"], v["should_contact"], reason,
                   needs_review=v["needs_review"])

    return out(config.DEFAULT_SETTING, True,
               f"routed to {segment} / {config.DEFAULT_SETTING}")

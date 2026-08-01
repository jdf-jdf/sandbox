"""
DOMAIN VERDICTS -- read side only.

Some addresses cannot be classified from the string alone. @med.cornell.edu
is a hospital and @cornell.edu is a university, and no amount of pattern
matching gets you there: the difference is a fact about the world, not a fact
about the text.

Facts about the world need research, and research is slow, costs money, and
returns a different answer depending on when you ask. None of that belongs in
the decision layer, which is supposed to be the part of the machine that
cannot get anything wrong.

So the research happens ONCE, out of band, in tools/classify_domains.py, and
lands in a JSON file. This module only reads that file. Everything here is
deterministic and offline: the same CSV plus the same cache always produces
the same decisions, the cache is a plain file a human can open and overrule,
and the run does not depend on a search engine being up.
"""
import json
import os

import config

_cache = None


def domain_of(address):
    """The domain part of an email address, lowercased. '' if there isn't one."""
    if "@" not in address:
        return ""
    return address.rsplit("@", 1)[-1].strip().lower().rstrip(".")


def needs_lookup(domain):
    """True if this domain is one the machine refuses to guess about."""
    return bool(domain) and domain.endswith(tuple(config.DOMAIN_LOOKUP_SUFFIXES))


def load(path=None, force=False):
    """Load the verdict file. Missing file is not an error: it means no domain
    has been researched yet, which the caller handles as 'suppress and tell
    the human', exactly like a domain that was researched inconclusively."""
    global _cache
    if _cache is not None and not force:
        return _cache
    path = path or config.DOMAIN_CACHE_PATH
    if not os.path.exists(path):
        _cache = {}
        return _cache
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    _cache = data.get("domains", {})
    return _cache


def lookup(domain):
    """Return the verdict record for a domain, or None if it has none.

    Subdomains do NOT inherit their parent's verdict. That is the whole point:
    med.cornell.edu and cornell.edu are different answers, and silently
    falling back to the parent would reintroduce the exact mistake this
    module exists to prevent.
    """
    return load().get(domain)


_CONFIDENCE_ORDER = {"low": 0, "medium": 1, "high": 2}


def resolve(domain, fallback_setting):
    """Map a domain to {setting, should_contact, needs_review, reason}.

    The setting comes back even when should_contact is False, so the run log
    and the review queue can say what the machine concluded rather than just
    that it declined.

    needs_review is the difference between a skip that is FINISHED and a skip
    that is WAITING. "Weill Cornell is an academic medical center" is finished:
    nobody needs to look at it again. "Never researched" and "researched, still
    not sure" are waiting, and they stay on the human's work order until
    somebody settles them. Without the distinction the queue fills with
    hundreds of correct, boring skips and the two that matter get lost.
    """
    def verdict_out(setting, should_contact, needs_review, reason):
        return {"setting": setting, "should_contact": should_contact,
                "needs_review": needs_review, "reason": reason}

    record = lookup(domain)
    if record is None:
        return verdict_out(fallback_setting, False, True,
                           f"suppressed pending review: {domain} has never been "
                           f"researched. Run tools/classify_domains.py, then rerun.")

    verdict = record.get("verdict", "")
    confidence = record.get("confidence", "low")
    why = (record.get("why") or "").strip()

    if verdict not in config.DOMAIN_VERDICT_SETTINGS:
        return verdict_out(fallback_setting, False, True,
                           f"suppressed pending review: {domain} came back "
                           f"{verdict!r}, which is not a verdict this machine "
                           f"acts on. Decide it by hand in "
                           f"{config.DOMAIN_CACHE_PATH}."
                           + (f" (research said: {why})" if why else ""))

    setting = config.DOMAIN_VERDICT_SETTINGS[verdict]

    # The institution changes the message, not whether there is one. Employed
    # clinicians move into private practice, and the one who cannot buy this
    # year picks the tools next year, so they get SETTING_BRIEF["institutional"]
    # rather than silence. Confidence does not gate this: the worst a wrong
    # verdict can do now is pick the wrong register.
    if setting == "institutional" and not config.SUPPRESS_INSTITUTIONAL:
        return verdict_out("institutional", True, False,
                           f"institutional ({domain}: {verdict})")

    # Suppression needs no confidence bar to take effect: declining to write to
    # a domain the research merely suspects is a health system costs one email,
    # and the opposite mistake is the one that matters. But a suppression
    # resting on less than full confidence is still an open question, so it
    # goes on the work order rather than quietly disappearing.
    if setting is None or setting == "institutional":
        settled = _CONFIDENCE_ORDER.get(confidence, 0) >= _CONFIDENCE_ORDER["high"]
        head = "suppressed" if settled else "suppressed pending review"
        tail = "" if settled else (
            f" Confidence was only {confidence}, so confirm it (or overrule it) "
            f"in {config.DOMAIN_CACHE_PATH}.")
        return verdict_out("institutional", False, not settled,
                           f"{head}: {domain} is a health system or medical "
                           f"organization, so nobody there can buy an EHR "
                           f"add-on. The touch is wasted and the send is noise."
                           + (f" ({why})" if why else "") + tail)

    floor = _CONFIDENCE_ORDER.get(config.DOMAIN_MIN_CONFIDENCE_TO_CONTACT, 2)
    if _CONFIDENCE_ORDER.get(confidence, 0) < floor:
        return verdict_out(fallback_setting, False, True,
                           f"suppressed pending review: {domain} looks like "
                           f"{verdict} but the research was only {confidence} "
                           f"confidence, and contacting needs "
                           f"{config.DOMAIN_MIN_CONFIDENCE_TO_CONTACT}. "
                           f"({why or 'no rationale given'}) Confirm it by hand "
                           f"in {config.DOMAIN_CACHE_PATH}.")

    return verdict_out(setting, True, False, f"{setting} ({domain}: {verdict})")

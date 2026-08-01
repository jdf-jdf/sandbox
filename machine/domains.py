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
    """Map a domain to (setting, should_contact, reason).

    The setting is returned even when should_contact is False, so the run log
    and the review queue can say what the machine concluded rather than just
    that it declined. The reason is written for the human reading
    REVIEW_QUEUE.md: it distinguishes "researched, and the answer is no" from
    "not researched yet", because those need different work.
    """
    record = lookup(domain)
    if record is None:
        return fallback_setting, False, (
            f"suppressed: {domain} has never been researched. "
            f"Run tools/classify_domains.py, then rerun.")

    verdict = record.get("verdict", "")
    confidence = record.get("confidence", "low")
    why = (record.get("why") or "").strip()

    if verdict not in config.DOMAIN_VERDICT_SETTINGS:
        return fallback_setting, False, (
            f"suppressed: {domain} came back {verdict!r}, which is not a "
            f"verdict this machine acts on. Decide it by hand in "
            f"{config.DOMAIN_CACHE_PATH}."
            + (f" (research said: {why})" if why else ""))

    setting = config.DOMAIN_VERDICT_SETTINGS[verdict]

    # Suppression needs no confidence bar. Declining to write to a domain the
    # research merely suspects is a health system costs one email; the
    # opposite mistake is the one that matters.
    if setting is None:
        return "institutional", False, (
            f"suppressed: {domain} is a health system or medical organization, "
            f"so nobody there can buy an EHR add-on. The touch is wasted and "
            f"the send is noise." + (f" ({why})" if why else ""))

    floor = _CONFIDENCE_ORDER.get(config.DOMAIN_MIN_CONFIDENCE_TO_CONTACT, 2)
    if _CONFIDENCE_ORDER.get(confidence, 0) < floor:
        return fallback_setting, False, (
            f"suppressed: {domain} looks like {verdict} but the research was "
            f"only {confidence} confidence, and contacting needs "
            f"{config.DOMAIN_MIN_CONFIDENCE_TO_CONTACT}. "
            f"({why or 'no rationale given'}) "
            f"Confirm it by hand in {config.DOMAIN_CACHE_PATH}.")

    return setting, True, f"{setting} ({domain}: {verdict})"

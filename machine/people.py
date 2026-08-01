"""
PERSON VERDICTS -- read side only.

The domain layer settles the institution. It cannot settle the person, and
the difference matters most exactly where the domain layer is least sure.

"Behavioral health clinician at a university address" does not mean trainee.
It means at a university. The same cornell.edu address fits a doctoral
student, a postdoc, a counseling-centre staff clinician, a training director,
and a tenured professor who keeps a small private caseload. Writing to a full
professor as though they were two years into a doctorate is not a near miss:
it insults the one person on that campus most able to influence what a
practice buys.

So `training` out of the domain layer is a HYPOTHESIS, not a verdict. This
module is the second lookup that either confirms it or throws it out.

Two rules make it trustworthy.

The first is the same as domains.py: research happens once, out of band, in
tools/classify_people.py, and lands in a JSON file that this module only ever
reads. Nothing here touches the network.

The second is specific to people. A title is not a durable fact. Doctoral
students graduate, residents finish, interns get licensed, and the web
remembers all of them as they were. A 2019 lab page calling someone a
doctoral candidate is evidence about 2019, and acting on it in 2026 sends the
trainee email to someone who has been licensed for years. So a verdict here
carries the DATE its evidence was published, and a title confirmed longer ago
than config.PERSON_EVIDENCE_MAX_AGE_MONTHS is treated as unproven rather than
as true.

That makes this layer deterministic given (cache, today) rather than given
(cache) alone, which is a deliberate trade. A stale verdict aging out into
"ask a human" is the behaviour we want; a stale verdict silently staying true
forever is the bug.
"""
import datetime
import json
import os

import config

_cache = None


def load(path=None, force=False):
    """Load the verdict file. A missing file means nobody has been researched
    yet, which callers handle as 'suppress and tell the human' -- the same way
    they handle a person researched inconclusively."""
    global _cache
    if _cache is not None and not force:
        return _cache
    path = path or config.PERSON_CACHE_PATH
    if not os.path.exists(path):
        _cache = {}
        return _cache
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    _cache = data.get("people", {})
    return _cache


def key(email):
    """Cache key for one person: their address, lowercased.

    The address rather than the name because two clinicians share a name far
    more often than they share an inbox, and because the id column belongs to
    whoever exported the CSV and can change between pulls.
    """
    return (email or "").strip().lower()


def lookup(email):
    """Return the verdict record for one person, or None."""
    return load().get(key(email))


def needs_lookup(setting):
    """True if this setting is a guess the person layer is meant to check."""
    return setting in tuple(config.PERSON_LOOKUP_SETTINGS)


def _parse_date(value):
    """Accept YYYY, YYYY-MM or YYYY-MM-DD. Returns a date, or None."""
    text = (value or "").strip()
    for fmt, pad in (("%Y-%m-%d", None), ("%Y-%m", "-01"), ("%Y", "-01-01")):
        try:
            return datetime.datetime.strptime(text + (pad or ""), "%Y-%m-%d").date()
        except ValueError:
            continue
    return None


def months_since(value, today=None):
    """Whole months between an evidence date and today. None if unparseable.

    Negative ages (a date in the future) are clamped to 0 rather than treated
    as fresh-forever, because the realistic cause is a typo in the cache.
    """
    when = _parse_date(value)
    if when is None:
        return None
    today = today or datetime.date.today()
    months = (today.year - when.year) * 12 + (today.month - when.month)
    if today.day < when.day:
        months -= 1
    return max(0, months)


_CONFIDENCE_ORDER = {"low": 0, "medium": 1, "high": 2}


def enrich(row):
    """Return the row with researched fields merged in.

    This is what makes a three-column list workable. The real export is name,
    email and mobile: there is no credential column to route on, so the
    machine goes and finds one and then routes on that. A researched
    credential is written into the row under the same name the CSV would have
    used, so config.SEGMENT_RULES and config.ROUTE_FIELDS need no special case
    and do not care where the value came from.

    The CSV always wins. If a list does arrive with a credential column, that
    is a human's assertion and it outranks anything a search inferred.
    """
    merged = dict(row)
    record = lookup(row.get(config.ADDRESS_FIELD, ""))
    for field in ("credential", "practice_type", "notes"):
        merged.setdefault(field, "")
    if not record:
        return merged

    for field, value in (("credential", record.get("credential", "")),
                         ("practice_type", record.get("title", ""))):
        if value and not merged.get(field):
            merged[field] = value
    return merged


def resolve(email, label, hypothesis, fallback_setting, today=None):
    """Map one person to {setting, should_contact, needs_review, reason}.

    `hypothesis` is what the domain layer guessed, carried through only so the
    reason line can say what was being checked. The verdict here overrides it
    in every branch: that is the entire point of the second lookup.

    needs_review marks the skips that are waiting on a person rather than
    finished. "Never researched" is work; "researched, and they are a
    professor" is a decision.
    """
    def out(setting, should_contact, reason, needs_review=False):
        return {"setting": setting, "should_contact": should_contact,
                "needs_review": needs_review, "reason": reason}

    who = f"{label} <{key(email)}>"
    record = lookup(email)

    if record is None:
        return out(fallback_setting, False,
                   f"suppressed pending review: {who} sits on a domain that "
                   f"only says {hypothesis!r}, and the person has never been "
                   f"researched. Run tools/classify_people.py, then rerun.",
                   needs_review=True)

    verdict = record.get("verdict", "")
    confidence = record.get("confidence", "low")
    title = (record.get("title") or "").strip()
    why = (record.get("why") or "").strip()
    evidence_date = record.get("evidence_date", "")

    if verdict not in config.PERSON_VERDICT_SETTINGS:
        return out(fallback_setting, False,
                   f"suppressed pending review: {who} came back {verdict!r}, "
                   f"which is not a verdict this machine acts on. Decide it by "
                   f"hand in {config.PERSON_CACHE_PATH}."
                   + (f" (research said: {why})" if why else ""),
                   needs_review=True)

    # --- the recency bar ---
    # Checked before the verdict is acted on, and before the confidence bar,
    # because a stale title is wrong regardless of how sure the research was
    # when it was written. "High confidence, seven years ago" is exactly the
    # combination that would otherwise sail through.
    age = months_since(evidence_date, today=today)
    limit = config.PERSON_EVIDENCE_MAX_AGE_MONTHS
    if age is None:
        return out(fallback_setting, False,
                   f"suppressed pending review: {who} is recorded as {verdict!r}"
                   f"{f' ({title})' if title else ''} but the record carries no "
                   f"usable evidence date, so there is nothing to say the title "
                   f"is current. Re-run tools/classify_people.py or date it by "
                   f"hand in {config.PERSON_CACHE_PATH}.",
                   needs_review=True)
    if age > limit:
        return out(fallback_setting, False,
                   f"suppressed pending review: {who} was confirmed as "
                   f"{verdict!r}{f' ({title})' if title else ''} {age} months "
                   f"ago, older than the {limit}-month bar. Titles expire: "
                   f"trainees finish. Re-run tools/classify_people.py "
                   f"--refresh-stale to confirm it still holds.",
                   needs_review=True)

    setting = config.PERSON_VERDICT_SETTINGS[verdict]

    # Suppression needs no confidence bar, same asymmetry as the domain layer.
    # Declining to write costs one email. Writing the trainee note to a
    # department chair costs the account.
    if setting is None:
        return out("institutional", False,
                   f"suppressed: {who} is {verdict}"
                   f"{f' ({title})' if title else ''}, not a trainee, and is "
                   f"employed by the institution rather than buying for "
                   f"themselves." + (f" ({why})" if why else ""))

    floor = _CONFIDENCE_ORDER.get(config.PERSON_MIN_CONFIDENCE_TO_CONTACT, 2)
    if _CONFIDENCE_ORDER.get(confidence, 0) < floor:
        return out(fallback_setting, False,
                   f"suppressed pending review: {who} looks like {verdict} but "
                   f"the research was only {confidence} confidence, and "
                   f"contacting needs {config.PERSON_MIN_CONFIDENCE_TO_CONTACT}. "
                   f"({why or 'no rationale given'}) Confirm it by hand in "
                   f"{config.PERSON_CACHE_PATH}.",
                   needs_review=True)

    detail = title or verdict
    return out(setting, True,
               f"{setting} ({label}: {detail}, confirmed {age}mo ago)")

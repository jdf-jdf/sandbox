"""
REPLY VERDICTS -- read side only.

Every axis in decide.py so far is inference: a domain researched once, a
title researched once. This one is different. A reply is the clinician
stating their own position on the exact question PROMPT now closes every
email with -- still turning it over, getting something set up, or already
running a practice of their own -- and a stated position outranks a guess
every time one is on file.

Same two rules as domains.py and people.py, because the shape of the problem
is identical:

  1. Classification happens ONCE, out of band, in tools/classify_replies.py,
     and lands in a JSON file. This module only ever reads it. Nothing here
     touches an inbox.

  2. The cache is a plain file a human can open and overrule. A machine that
     silently reclassifies a reply on every run is a machine nobody can audit.

STUBBED FOR THIS DEMO. tools/classify_replies.py reads data/reply_sample.jsonl
-- hand-written reply text, not a real inbox -- and classifies it by keyword
match, not by a model. Every record this module reads back carries
config.REPLY_STUB_SOURCE so nothing here is mistaken for the real thing. What
IS real: the cache format, the token resolution that ties a reply to a
clinician (machine/attribution.py), and the routing effect below. Point
tools/classify_replies.py at a real inbox and a real classifier, and nothing
in decide.py or run.py has to change.
"""
import json
import os

import config

_cache = None


def load(path=None, force=False):
    """Load the verdict file. Missing file means nobody has replied yet,
    which callers handle as "nothing to override" -- the same way an
    unresearched domain falls through rather than failing."""
    global _cache
    if _cache is not None and not force:
        return _cache
    path = path or config.REPLY_CACHE_PATH
    if not os.path.exists(path):
        _cache = {}
        return _cache
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    _cache = data.get("people", {})
    return _cache


def key(clinician_id):
    """Cache key: the row's own id, not the email. A reply is resolved off an
    attribution token, and a token resolves to an id (machine/attribution.py),
    not an address -- the mailbox that received a campaign email and the one
    a clinician chooses to reply from are not guaranteed to be the same box.
    """
    return str(clinician_id or "").strip()


def lookup(clinician_id):
    """Return the verdict record for one clinician, or None."""
    return load().get(key(clinician_id))


def enrich(row):
    """Fold a reply verdict's own words into the row's `notes` field.

    This is what lets the NEXT draft honestly reference what they said
    instead of the model inventing it: REFUSAL_RULES blocks
    fabricated_relationship precisely because nothing is usually on file.
    Once someone has replied, something genuinely is.

    A `notes` value already on the row (from the CSV, or filled by an earlier
    pass) wins: this only fills a blank, never overwrites what a human or
    another layer already put there.
    """
    merged = dict(row)
    if merged.get("notes"):
        return merged
    record = lookup(row.get(config.ID_FIELD, ""))
    if record is None:
        return merged
    why = (record.get("why") or "").strip()
    if why:
        merged["notes"] = config.REPLY_NOTE_TEMPLATE.format(
            seen_at=record.get("seen_at") or "an earlier reply", why=why)
    return merged


def resolve(clinician_id):
    """Map a cached reply verdict to a routing override, or None.

    None means "nothing to override": either nobody has replied, or they
    replied with one of the two still-getting-there practice-path answers
    (thinking_about_opening_practice, not_yet_opening_practice), which are
    informational rather than a reason to change should_contact or setting.
    decide.py falls through to its normal routing in both cases -- the reply
    is not silence, but it isn't a redirect either.
    """
    record = lookup(clinician_id)
    if record is None:
        return None
    disposition = record.get("disposition", "unclear")
    effect = config.REPLY_OVERRIDES.get(disposition)
    if effect is None:
        return None
    return dict(effect, disposition=disposition)

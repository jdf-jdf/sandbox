#!/usr/bin/env python3
"""
Turn replies into routing facts, once, out of band.

    python tools/classify_replies.py            # classify what isn't cached
    python tools/classify_replies.py --dry      # show the work, write nothing
    python tools/classify_replies.py --refresh  # re-classify everything
    python tools/classify_replies.py --inbound FILE

Why this exists.

Every other axis in decide.py is inference. The domain was researched once,
the title was researched once, and both are the machine's best guess about
somebody it has never spoken to. A reply is not a guess: it is the clinician
answering, in their own words, the exact question PROMPT closes every email
with. A stated position outranks an inferred one, so this runs ahead of the
domain and person caches in decide.route().

The shape is deliberately identical to classify_domains.py and
classify_people.py: read something out of band, write a JSON file, and let the
decision layer do nothing but read it. That keeps the run deterministic and
offline, and it means a human can open data/reply_verdicts.json and overrule
any line the classifier got wrong.

WHAT IS REAL AND WHAT IS STUBBED, precisely.

Real: the token resolution. A reply carries the attribution token the send
left behind (machine/attribution.py), so "someone replied" resolves to "C-110
Elena Sokolova, from run 1" by dictionary lookup and no fuzzy name matching.
Real: the cache format, and the routing effect in machine/replies.py.

Stubbed: the classifier itself and the inbox. This reads a hand-written
JSONL file rather than IMAP, and sorts text by keyword rather than by model.
Every record it writes carries `"source": "keyword_stub"` so nothing
downstream can mistake it for judgment. A real version swaps the two
functions below for an inbox client and a model call; nothing in
machine/replies.py or decide.py changes, because neither knows how the file
was written.

Why keyword and not a model, for a demo: a keyword table is auditable at a
glance and identical on every run, which is the right trade for a stub whose
job is to prove the plumbing. A model here would be more accurate and less
inspectable, and it is the one place in this repo where a wrong answer
silently reverses a suppression decision.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from run import load_dotenv  # noqa: E402
import config  # noqa: E402
from machine import attribution, replies  # noqa: E402

DEFAULT_INBOUND = "data/reply_sample.jsonl"

# Order is load-bearing. "not interested" contains "interested", and a warm
# lead wrongly suppressed is a cheaper mistake than an opt-out wrongly
# contacted -- so the refusals are tested first and win outright.
#
# Each entry: (disposition, [phrases]). Matched on whole phrases against the
# lowercased reply, because single keywords ("open", "set up", "running")
# appear in half of all sentences and would misfile most of them.
RULES = [
    ("not_interested", [
        "not interested", "no thanks", "no thank you", "unsubscribe",
        "take me off", "remove me", "stop emailing", "stop contacting",
        "opt out", "do not contact", "please don't email",
    ]),
    ("in_practice", [
        "already running", "up and running", "running my own", "running it",
        "i opened", "opened my own", "opened last", "in practice",
        "been in private practice", "my own practice now", "years now",
    ]),
    ("not_yet_opening_practice", [
        "getting set up", "setting up", "credentialing", "sign a lease",
        "signing a lease", "about to open", "opening in", "opening next",
        "not open yet", "almost there", "in the process of opening",
    ]),
    ("thinking_about_opening_practice", [
        "thinking about", "turning it over", "still turning", "considering",
        "toying with", "on the fence", "staying put", "not sure yet",
        "someday", "one day",
    ]),
    ("interested", [
        "interested", "tell me more", "send me", "what does it cost",
        "what's the pricing", "how much", "worth a look", "happy to talk",
        "would like to hear",
    ]),
]


def classify(text):
    """(disposition, matched_phrase). 'unclear' when nothing matches.

    Unclear is a real answer and not a failure: machine/replies.py routes it
    to a human rather than guessing, which is the same instinct as an
    unresearched domain. A reply nobody can read is exactly the case where a
    wrong guess reverses a suppression.
    """
    probe = (text or "").lower()
    for disposition, phrases in RULES:
        for phrase in phrases:
            if re.search(rf"(?<!\w){re.escape(phrase)}", probe):
                return disposition, phrase
    return "unclear", ""


def resolve_sender(signal):
    """Which clinician sent this. Returns (id, how) or (None, reason).

    The token is the real mechanism and is tried first: it came off our own
    send, so it needs no interpretation. The `id` field is a convenience for
    hand-written samples, and a real collector would usually carry only the
    token.
    """
    tok = (signal.get("token") or "").strip()
    if tok:
        entry = attribution.resolve_token(tok)
        if entry:
            return entry["id"], f"token {tok}"
    given = (signal.get("id") or "").strip()
    if given:
        return given, "id in the signal (no ledger match for its token)"
    return None, f"unresolvable: token {tok!r} matches no send, and no id given"


def load_inbound(path):
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Inbound file not found: {path}\n"
            f"This stub reads replies from a file. Point --inbound at one.")
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def save(cache, path):
    """Write atomically, same as the other two caches: a half-written verdict
    file read by the next run is worse than no verdict file at all."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"version": 1, "people": cache}, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inbound", default=DEFAULT_INBOUND)
    ap.add_argument("--dry", action="store_true",
                    help="show what would be written, write nothing")
    ap.add_argument("--refresh", action="store_true",
                    help="re-classify replies already in the cache")
    args = ap.parse_args()

    load_dotenv()
    cache = dict(replies.load(force=True))
    signals = load_inbound(args.inbound)

    print(f"\n{len(signals)} reply/replies in {args.inbound}")
    print(f"classifier: {config.REPLY_STUB_SOURCE} "
          f"({sum(len(p) for _, p in RULES)} phrases, "
          f"{len(RULES)} dispositions)\n")

    written, skipped, unresolved = 0, 0, 0
    for signal in signals:
        clinician_id, how = resolve_sender(signal)
        if clinician_id is None:
            print(f"  {'?':<8} {how}")
            unresolved += 1
            continue

        if replies.key(clinician_id) in cache and not args.refresh:
            print(f"  {clinician_id:<8} already cached, skipping (--refresh to redo)")
            skipped += 1
            continue

        disposition, matched = classify(signal.get("text", ""))
        record = {
            "disposition": disposition,
            "why": (signal.get("text") or "").strip(),
            "seen_at": signal.get("seen_at", ""),
            "matched": matched,
            "resolved_by": how,
            "source": config.REPLY_STUB_SOURCE,
        }
        cache[replies.key(clinician_id)] = record
        written += 1

        effect = config.REPLY_OVERRIDES.get(disposition)
        if effect is None:
            mark = "informational, routing unchanged"
        elif effect["should_contact"]:
            mark = f"-> {effect['setting']}"
        elif effect["needs_review"]:
            mark = "-> HELD for a human"
        else:
            mark = "-> SUPPRESSED"
        print(f"  {clinician_id:<8} {disposition:<32} {mark}")
        if matched:
            print(f"  {'':<8} matched {matched!r}")

    if args.dry:
        print(f"\n--dry: {written} would be written, nothing saved.")
        return 0

    if written:
        save(cache, config.REPLY_CACHE_PATH)
        print(f"\nwrote {len(cache)} verdict(s) -> {config.REPLY_CACHE_PATH}")
        print("Read them. A reply is someone's own words about their own "
              "practice, and\nthe machine now routes on it: anything wrong, "
              "edit the file. The run trusts\nit over every other axis.")
    else:
        print(f"\nNothing new. {len(cache)} verdict(s) already in "
              f"{config.REPLY_CACHE_PATH}.")
    if unresolved:
        print(f"\n{unresolved} reply/replies could not be tied to a send. "
              f"Each one is a\nhole in the plumbing, not a clinician to chase.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
NOTICE THE MOMENT -- turn inbound signals back into named clinicians.

    python tools/returns.py                     # the impact report
    python tools/returns.py --inbound FILE      # read a different signal file

The brief asks two things of the win-back: stay alive with these clinicians
until their timing turns, and NOTICE THE MOMENT IT DOES. Sending is the first
half and the easy half. This is the second.

It works because every send left a token behind (machine/attribution.py), and
the token is on all three doors a clinician can come back through:

    click   jotpsych.com/welcome-back/<token>   -> web log
    reply   jo+<token>@gmail.com                -> inbox
    text    the mobile number on the row        -> matched on the number

So an inbound signal does not need to be understood, parsed, or matched
fuzzily by name. It carries its own answer. "Someone came back" resolves to
"C-126 Marcus Feld, prescriber, practice owner, from run 5, 14 days after we
wrote" with a dictionary lookup and no guessing.

WHAT IS REAL AND WHAT IS SKETCHED
Real: the tokens, the ledger, the resolution, and every number below.
Sketched: the collectors. Reading the actual web log, the actual inbox and
the actual SMS webhook is three integrations, and the brief says to simulate
what is sketched. data/inbound_sample.jsonl stands in for all three, in the
shape the real collectors would emit. Point --inbound at a real export and
nothing else changes.
"""
import argparse
import collections
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402
from machine import attribution  # noqa: E402

DEFAULT_INBOUND = "data/inbound_sample.jsonl"


def load_inbound(path):
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _days_between(sent_at, seen_at):
    """Whole days from send to signal. None if either stamp is unusable."""
    def parse(value):
        text = (value or "").strip()
        for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.datetime.strptime(text, fmt).replace(tzinfo=None)
            except ValueError:
                continue
        return None
    a, b = parse(sent_at), parse(seen_at)
    return (b - a).days if a and b else None


def match(signals, ledger):
    """Resolve every inbound signal to the send that earned it.

    Two keys, tried in order. The token is exact and needs no interpretation.
    The mobile number is the fallback for the one door that cannot carry a
    token: somebody who texts the number back is identified by the number
    they texted from, which is why the export's third column earns its place.
    """
    by_token = {(e["token"] or "").strip().lower(): e for e in ledger}
    by_mobile = {}
    for e in ledger:                       # newest send per number wins
        if e.get("mobile"):
            by_mobile[e["mobile"]] = e

    matched, orphans = [], []
    for sig in signals:
        entry = None
        if sig.get("token"):
            entry = by_token.get((sig["token"] or "").strip().lower())
        if entry is None and sig.get("from_mobile"):
            entry = by_mobile.get(sig["from_mobile"])
        if entry is None:
            orphans.append(sig)
            continue
        matched.append({
            "signal": sig, "send": entry,
            "days": _days_between(entry.get("sent_at"), sig.get("seen_at")),
        })
    return matched, orphans


def report(ledger, matched, orphans, dry=0):
    sends = len(ledger)
    people = len({e["id"] for e in ledger})
    returned = {m["send"]["id"] for m in matched}

    print("\n=== IMPACT ===")
    print(f"  sends              {sends} across {people} clinician(s)")
    if dry:
        print(f"  (excluded          {dry} dry-run row(s): drafted, never emailed)")
    print(f"  signals in         {len(matched) + len(orphans)}")
    print(f"  resolved to a send {len(matched)}")
    print(f"  clinicians back    {len(returned)}"
          f"  ({(len(returned) / people * 100) if people else 0:.1f}% of those written to)")
    if orphans:
        print(f"  unattributable     {len(orphans)}  <- came back, but not "
              f"traceably. Every one of these is a hole in the plumbing.")

    if matched:
        lags = [m["days"] for m in matched if m["days"] is not None]
        if lags:
            lags.sort()
            print(f"  days to return     median {lags[len(lags) // 2]}, "
                  f"range {lags[0]}-{lags[-1]}")

        by_channel = collections.Counter(m["signal"].get("channel", "?")
                                         for m in matched)
        print("\n  by door:")
        for channel, n in by_channel.most_common():
            print(f"    {channel:<10} {n}")

        by_segment = collections.Counter(
            f"{m['send'].get('segment', '?')} / {m['send'].get('setting', '?')}"
            for m in matched)
        print("\n  who comes back:")
        for seg, n in by_segment.most_common():
            print(f"    {seg:<28} {n}")

        print("\n  the returns themselves:")
        for m in sorted(matched, key=lambda m: m["days"] if m["days"] is not None else 0):
            s, e = m["signal"], m["send"]
            lag = f"{m['days']}d" if m["days"] is not None else "?"
            print(f"    {e['name']:<20} {e['id']:<7} run {e['run']}  "
                  f"{s.get('channel', '?'):<9} +{lag:<5} {s.get('note', '')[:44]}")

    print("\n  This is the number the machine exists to move. Everything else "
          "it reports\n  (rejection rate, suppression, queue depth) is process. "
          "This is outcome.\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inbound", default=DEFAULT_INBOUND)
    args = ap.parse_args()

    # A dry run is recorded too, and a dry run is not a send. Filtered here
    # rather than inside report() so that matching cannot resolve an inbound
    # signal to an email that never left the building -- a click on a link
    # nobody was ever given is a bug in the collector, not a return.
    everything = attribution.load_ledger()
    ledger = [e for e in everything if attribution.was_live(e)]
    if not ledger:
        if everything:
            print(f"\n{len(everything)} row(s) in {config.ATTRIBUTION_LEDGER_PATH}, "
                  f"but every one of them is a dry run. Nothing has actually "
                  f"been emailed, so there is nothing that could come back.\n"
                  f"Run `python run.py --send` first.\n")
        else:
            print(f"\nNo sends recorded in {config.ATTRIBUTION_LEDGER_PATH}. "
                  f"Run the machine first.\n")
        return 1

    signals = load_inbound(args.inbound)
    if not signals:
        print(f"\nNo inbound signals in {args.inbound}. Nothing has come back "
              f"yet, which after one run is the expected answer.\n")
        return 0

    matched, orphans = match(signals, ledger)
    report(ledger, matched, orphans, dry=len(everything) - len(ledger))
    return 0


if __name__ == "__main__":
    sys.exit(main())

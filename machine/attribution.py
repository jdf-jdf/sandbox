"""
ATTRIBUTION -- how a return gets traced back to the machine.

The brief asks that when a dormant clinician comes back, we can trace the
return to the machine. That is not a reporting problem, it is a plumbing
problem, and it has to be solved at the moment of sending or it cannot be
solved at all: once an email goes out untagged, nothing downstream can
recover which send earned the reply.

Three tags, because clinicians come back through three different doors and
each door drops a different one:

  the link    they click through and land on the site
  the reply   they hit reply and it arrives in an inbox
  the phone   they text or call the number back

All three carry the same token, so all three resolve to one row and one run.

The token is derived, not random. Deriving it means the ledger can be rebuilt
from the CSV plus the run number if it is ever lost, and that a rerun of the
same row in the same run produces the same token rather than a second one
that looks like a second person. It is an HMAC rather than a plain hash so
the id cannot be recovered from a token that appears in a public URL or a web
log: attribution should not leak a customer list.

The ledger is written on every send, including dry runs, so there is a record
of what was promised even when the email path is unavailable.
"""
import hashlib
import hmac
import json
import os
import time

import config


def _secret():
    """Key for the token HMAC.

    Falls back to a constant so a fresh checkout runs without setup. That
    fallback is fine for a sample and wrong for production, where the tokens
    become guessable, so it says so out loud rather than failing silently.
    """
    return (os.environ.get("ATTRIBUTION_SECRET") or "sample-key-not-secret").encode()


def token(row, run_no):
    """Short, stable, opaque handle for one row in one run."""
    msg = f"{row[config.ID_FIELD]}:{run_no}".encode()
    digest = hmac.new(_secret(), msg, hashlib.sha256).hexdigest()
    return digest[:config.ATTRIBUTION_TOKEN_CHARS]


def link(tok):
    """The click door."""
    return config.ATTRIBUTION_LINK_TEMPLATE.format(token=tok)


def reply_to(tok):
    """The reply door.

    Plus-addressing, so every clinician gets a distinct Reply-To that still
    lands in one mailbox with no new infrastructure. The local part is the
    token, so an inbox rule can attribute a reply without opening it.
    """
    address = os.environ.get("GMAIL_ADDRESS", "")
    if "@" not in address:
        return ""
    local, _, host = address.partition("@")
    return f"{local}+{tok}@{host}"


def stamp(text, tok):
    """Append the tracked line to an approved draft.

    Deliberately after the QC gate rather than inside the prompt. A model
    asked to place a URL will sometimes reword it, wrap it, or drop it, and a
    tracking link that is only usually present is not a tracking link. The
    gate reads the copy; this adds the plumbing to copy that already passed.
    """
    return f"{text.rstrip()}\n\n{config.ATTRIBUTION_FOOTER.format(link=link(tok))}\n"


def record(row, decision, run_no, tok, channel_results, path=None, live=False):
    """Append one line to the ledger. One JSON object per line, so the file
    can be tailed, grepped, and appended to concurrently without a parser.

    `live` is the difference between "this reached an inbox" and "this is what
    a dry run would have sent". Both belong in the ledger -- a dry run leaving
    no trace of what it promised is worse -- but only one of them is a send,
    and conflating them overstates every outcome number downstream.
    """
    path = path or config.ATTRIBUTION_LEDGER_PATH
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    entry = {
        "token": tok,
        "id": row.get(config.ID_FIELD, ""),
        "name": row.get(config.LABEL_FIELD, ""),
        "address": row.get(config.ADDRESS_FIELD, ""),
        "mobile": row.get("mobile", ""),
        "run": run_no,
        "live": bool(live),
        "sent_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "segment": decision.get("segment", ""),
        "setting": decision.get("setting", ""),
        "link": link(tok),
        "reply_to": reply_to(tok),
        "channels": channel_results,
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry


def load_ledger(path=None):
    """Every send the machine has ever made, oldest first."""
    path = path or config.ATTRIBUTION_LEDGER_PATH
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def was_live(entry):
    """True if this ledger line represents an email that actually went out.

    Lines written before the flag existed do not carry it. Rather than reading
    an old ledger as all-dry (which would report zero sends and zero returns
    for work that demonstrably happened), those fall back to the channel
    results: an entry the SMTP sender touched says "emailed ...".
    """
    if "live" in entry:
        return bool(entry["live"])
    return any("emailed" in str(c) for c in entry.get("channels", []))


def resolve_token(tok, path=None):
    """Given a token off a click, a reply address, or an inbound text, return
    the send it came from. This is the whole point of the module."""
    tok = (tok or "").strip().lower()
    if "@" in tok:                       # a full plus-address was pasted in
        tok = tok.partition("@")[0].rpartition("+")[2]
    for entry in load_ledger(path):
        if entry["token"] == tok:
            return entry
    return None

#!/usr/bin/env python3
"""
Re-read the brand before the machine writes in its voice.

    python tools/brand_check.py            # fetch, diff, write the work order
    python tools/brand_check.py --dry      # list the pages, fetch nothing
    python tools/brand_check.py --refresh  # ignore the snapshot, re-read all
    python tools/brand_check.py --send     # also email marketing (see below)

Why this exists:

The prompt described JotPsych as "an ambient AI scribe" for two years after it
stopped being one. Every email the machine wrote pitched a product the whole
list had already left, and nothing inside the machine could notice, because
nothing inside the machine was looking. The QC gate is an opinion about how we
sound. It has never had an opinion about whether we are still describing the
right company.

So: once a month, before the run. Read the pages, diff them against last
month, ask marketing what is coming that is not on the site yet, and put what
changed in front of a human.

What it deliberately does not do:

Edit config.py or BRAND.md. A machine that rewrites its own voice from a
scraped diff is one bad parse away from sending something nobody approved, and
brand copy is the single place in this system where a human in the loop is the
point rather than the overhead. This writes a work order. A person spends ten
minutes on it and the machine is current for another month. That is most of
what the monthly hour is for.

Out of band for the same reason the domain research is: the run itself stays
deterministic and offline, and a site being down or a search being slow can
never change who gets contacted today.
"""
import argparse
import datetime
import difflib
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from run import load_dotenv  # noqa: E402
import config  # noqa: E402
from machine import send as send_mod  # noqa: E402

# Some sites answer a bare urllib request with a challenge page. Identifying
# the machine honestly gets a normal response and is the polite thing to do
# when reading someone's site on a schedule.
USER_AGENT = "JotPsychWinbackMachine/1.0 (brand check; +https://jotpsych.com)"
FETCH_TIMEOUT = 20

RECORD_TOOL = {
    "name": "record_brand_change",
    "description": "Record what changed on this page. Call exactly once.",
    "input_schema": {
        "type": "object",
        "properties": {
            "severity": {
                "type": "string",
                "enum": ["none", "cosmetic", "material"],
                "description": "material = the machine would now describe the "
                               "product wrongly if nobody acts on this.",
            },
            "summary": {
                "type": "string",
                "description": "One or two sentences, plain. What changed.",
            },
            "positioning_now": {
                "type": "string",
                "description": "The company's current one-line description of "
                               "itself, verbatim, if this page carries it. "
                               "Empty string if it does not.",
            },
            "new_modules": {
                "type": "array", "items": {"type": "string"},
                "description": "Product or module names present now and absent "
                               "before.",
            },
            "gone_modules": {
                "type": "array", "items": {"type": "string"},
                "description": "Names that were there before and are not now.",
            },
            "new_claims": {
                "type": "array", "items": {"type": "string"},
                "description": "Statistics or claims stated now, verbatim, that "
                               "were not stated before.",
            },
            "gone_claims": {
                "type": "array", "items": {"type": "string"},
                "description": "Claims withdrawn since last time. These matter "
                               "most: we may still be repeating them.",
            },
            "price_changes": {
                "type": "array", "items": {"type": "string"},
                "description": "Plan name and what its price moved from and to.",
            },
            "actions": {
                "type": "array", "items": {"type": "string"},
                "description": "What a human should change, named concretely: "
                               "which constant in config.py, which section of "
                               "BRAND.md. Empty if nothing needs doing.",
            },
        },
        "required": ["severity", "summary", "positioning_now", "new_modules",
                     "gone_modules", "new_claims", "gone_claims",
                     "price_changes", "actions"],
        "additionalProperties": False,
    },
}


class _Text(HTMLParser):
    """Visible text only. Enough HTML handling for a marketing page, and no
    dependency: the repo has exactly one, and a brand check is not the reason
    to add a second."""

    SKIP = {"script", "style", "noscript", "svg", "head"}

    def __init__(self):
        super().__init__()
        self.parts = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data):
        if not self._skip_depth and data.strip():
            self.parts.append(data.strip())


def page_text(html_text):
    """Readable text, whitespace collapsed, one line per block.

    Normalised hard on purpose. A diff that fires because the CDN reflowed the
    markup is a diff nobody reads twice.
    """
    p = _Text()
    p.feed(html_text)
    text = "\n".join(p.parts)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def fetch(url):
    """Return page text, or raise. One page failing must not stop the rest."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as r:
        charset = r.headers.get_content_charset() or "utf-8"
        return page_text(r.read().decode(charset, errors="replace"))


def fetch_variants(url, samples):
    """Read the same URL a few times and return the distinct texts.

    jotpsych.com rotates its hero: the same URL served "the behavioral health
    AI scribe that defends you from insurance companies", "the behavioral
    health EHR that defends you from insurance companies" and "Your whole
    behavioral health practice. One system." on three consecutive reads. One
    fetch would therefore report a rewritten homepage most months, which is
    the specific way a monitor becomes something people stop reading.
    """
    seen = {}
    for _ in range(max(1, samples)):
        text = fetch(url)
        seen.setdefault(hashlib.sha256(text.encode("utf-8")).hexdigest(), text)
    return seen


def closest(text, known):
    """The previously-seen variant this one most resembles, for diffing.

    Diffing a new hero against an unrelated variant produces a diff that is
    all noise. Matching to the nearest known text first means the diff shows
    what actually moved.
    """
    if not known:
        return ""
    return max(known.values(),
               key=lambda k: difflib.SequenceMatcher(None, k, text).ratio())


def load_snapshot(path):
    """Read the snapshot, upgrading the v1 single-text shape on the way.

    v1 stored one text per URL, which is what assuming a page is a page gets
    you. v2 stores every variant ever seen. Old files are migrated rather than
    discarded so the first run after this change is not a false alarm on
    everything at once.
    """
    empty = {"version": 2, "checked_at": None, "pages": {}}
    if not os.path.exists(path):
        return empty
    with open(path, encoding="utf-8") as f:
        snap = json.load(f)
    if snap.get("version", 1) >= 2:
        return snap
    pages = {}
    for url, rec in (snap.get("pages") or {}).items():
        text, digest = rec.get("text", ""), rec.get("sha256")
        stamp = rec.get("fetched_at")
        pages[url] = {"variants": ({digest: {"text": text, "first_seen": stamp,
                                             "last_seen": stamp}}
                                   if text and digest else {})}
    return {"version": 2, "checked_at": snap.get("checked_at"), "pages": pages}


def save_snapshot(snap, path):
    """Atomic, so a half-written snapshot can never become next month's
    baseline."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(snap, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)


def text_diff(old, new, url):
    """Unified diff, for the human and for the record.

    Produced whether or not the model is reachable. When the API is down this
    is still a usable answer: a person can read a diff.
    """
    lines = list(difflib.unified_diff(
        old.splitlines(), new.splitlines(),
        fromfile=f"{url} (last month)", tofile=f"{url} (now)",
        lineterm="", n=1,
    ))
    return "\n".join(lines)


def _extract(content):
    for block in content:
        if getattr(block, "type", None) == "tool_use" and block.name == RECORD_TOOL["name"]:
            return block.input
    return None


def analyse(client, url, old, new):
    """One page, one verdict. Returns a record dict, always."""
    blank = {
        "severity": "unknown", "summary": "", "positioning_now": "",
        "new_modules": [], "gone_modules": [], "new_claims": [],
        "gone_claims": [], "price_changes": [], "actions": [],
    }
    if client is None:
        return dict(blank, summary="No API key, so the diff below is unread. "
                                   "Read it yourself.")

    cap = config.BRAND_CHECK_MAX_CHARS
    prompt = config.BRAND_CHECK_PROMPT.format(
        url=url, old=(old or "(this page was not in the snapshot)")[:cap],
        new=new[:cap])
    messages = [{"role": "user", "content": prompt}]
    try:
        for _ in range(3):
            resp = client.messages.create(
                model=config.MODEL,
                max_tokens=config.MAX_TOKENS,
                thinking={"type": "adaptive"},
                tools=[RECORD_TOOL],
                messages=messages,
            )
            found = _extract(resp.content)
            if found:
                return dict(blank, **found)
            messages.append({"role": "assistant", "content": resp.content})
            messages.append({"role": "user",
                             "content": "Call record_brand_change now."})
    except Exception as e:  # noqa: BLE001 -- one page must not end the check
        return dict(blank, summary=f"analysis failed: {type(e).__name__}: {e}")
    return dict(blank, summary="model never called the tool; read the diff.")


def _bullets(title, items):
    if not items:
        return ""
    return f"\n**{title}**\n\n" + "\n".join(f"- {i}" for i in items) + "\n"


def write_review(results, path, checked_at):
    """The work order. One file, ordered worst first, so the monthly ten
    minutes is spent on the thing that matters rather than on triage."""
    order = {"material": 0, "unknown": 1, "cosmetic": 2, "none": 3, "error": 4}
    ranked = sorted(results, key=lambda r: order.get(r["record"]["severity"], 9))
    material = [r for r in ranked if r["record"]["severity"] == "material"]

    out = [
        "# Brand review",
        "",
        f"Checked {checked_at}. Sources: "
        + ", ".join(f"`{r['url']}`" for r in results),
        "",
    ]
    if not material:
        out += ["Nothing material changed. The machine's brand facts still "
                "match the site, and `BRAND.md` needs no edit this month.", ""]
    else:
        out += [f"**{len(material)} page(s) changed materially.** Until someone "
                "acts on this, the machine is describing the product as it was "
                "last month.", ""]

    for r in ranked:
        rec, url = r["record"], r["url"]
        out += [f"## {url}", "", f"*severity: {rec['severity']}*", ""]
        if r.get("error"):
            out += [f"Could not read the page: {r['error']}", ""]
            continue
        if r.get("variants"):
            out += [f"*{r['fresh']} new variant(s) this month, "
                    f"{r['variants']} known in total. This URL does not serve "
                    f"one fixed page.*", ""]
        if rec["summary"]:
            out += [rec["summary"], ""]
        if rec["positioning_now"]:
            out += [f"> {rec['positioning_now']}", ""]
        for title, key in (("New product names", "new_modules"),
                           ("Product names no longer on the page", "gone_modules"),
                           ("New claims", "new_claims"),
                           ("Claims withdrawn (check we are not still using these)",
                            "gone_claims"),
                           ("Price changes", "price_changes"),
                           ("Do this", "actions")):
            block = _bullets(title, rec.get(key) or [])
            if block:
                out.append(block)
        if r["diff"]:
            out += ["<details><summary>Raw diff</summary>", "",
                    "```diff", r["diff"][:8000], "```", "", "</details>", ""]
        else:
            out += ["Nothing served this month that we had not already "
                    "recorded.", ""]

    out += ["---", "",
            "Nothing here is applied automatically. Edit `BRAND.md` first, "
            "since it carries the citations, then the constants in section 3a "
            "of `config.py` that quote it.", ""]

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    return path


def changes_paragraph(results):
    """The site half of the email to marketing, in prose rather than diff."""
    lines = []
    for r in results:
        rec = r["record"]
        if r.get("error"):
            lines.append(f"- {r['url']}: could not read it ({r['error']}).")
        elif rec["severity"] in ("none",) and not r["diff"]:
            lines.append(f"- {r['url']}: unchanged.")
        else:
            lines.append(f"- {r['url']}: {rec['summary'] or 'text changed.'}")
    return "\n".join(lines) if lines else "- nothing read this month."


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true",
                    help="list the pages and exit, fetching nothing")
    ap.add_argument("--refresh", action="store_true",
                    help="ignore the snapshot and treat every page as new")
    ap.add_argument("--send", action="store_true",
                    help="also email the brand contact (honours SEND_TO)")
    ap.add_argument("--force", action="store_true",
                    help="permit sending to the real BRAND_CONTACT address")
    args = ap.parse_args()

    load_dotenv()

    if args.dry:
        print("would read:")
        for url in config.BRAND_SOURCES:
            print(f"  {url}")
        print(f"\nsnapshot: {config.BRAND_SNAPSHOT_PATH}")
        print(f"work order: {config.BRAND_REVIEW_PATH}")
        return 0

    snap = load_snapshot(config.BRAND_SNAPSHOT_PATH)
    pages = {} if args.refresh else dict(snap.get("pages", {}))

    client = None
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            import anthropic
            client = anthropic.Anthropic()
        except Exception as e:  # noqa: BLE001
            print(f"  ! anthropic client unavailable ({e}); diffs only")
    else:
        print("  ! ANTHROPIC_API_KEY unset; producing diffs without analysis")

    results = []
    now = datetime.datetime.now().isoformat(timespec="seconds")
    for url in config.BRAND_SOURCES:
        print(f"[read]     {url}")
        try:
            seen_now = fetch_variants(url, config.BRAND_SAMPLES)
        except (urllib.error.URLError, OSError, ValueError) as e:
            print(f"           FAILED {type(e).__name__}: {e}")
            results.append({
                "url": url, "diff": "", "error": f"{type(e).__name__}: {e}",
                "fresh": 0, "variants": 0,
                "record": dict(severity="error", summary="", positioning_now="",
                               new_modules=[], gone_modules=[], new_claims=[],
                               gone_claims=[], price_changes=[], actions=[]),
            })
            continue

        known = dict((pages.get(url) or {}).get("variants") or {})
        known_text = {d: v["text"] for d, v in known.items()}
        fresh = {d: t for d, t in seen_now.items() if d not in known}

        if not fresh:
            print(f"           unchanged ({len(seen_now)} variant(s) seen, "
                  f"{len(known)} on file, none new)")
            record = dict(severity="none",
                          summary="Nothing new. Every variant served this "
                                  "month has been seen before.",
                          positioning_now="", new_modules=[], gone_modules=[],
                          new_claims=[], gone_claims=[], price_changes=[],
                          actions=[])
            diff = ""
        else:
            # One analysis per page, spent on the most novel thing served.
            # Analysing every fresh variant would multiply cost for a page
            # that is merely rotating its hero faster than we sample it.
            novel = min(fresh.values(),
                        key=lambda t: difflib.SequenceMatcher(
                            None, closest(t, known_text), t).ratio())
            base = closest(novel, known_text)
            diff = text_diff(base, novel, url)
            record = analyse(client, url, base, novel)
            if len(fresh) > 1:
                record["summary"] = (f"{len(fresh)} previously unseen variants "
                                     f"this month. Most novel one: "
                                     f"{record['summary']}")
            print(f"           {record['severity']}: {record['summary'][:80]}")

        for digest, text in seen_now.items():
            entry = known.get(digest) or {"text": text[:config.BRAND_CHECK_MAX_CHARS],
                                          "first_seen": now}
            entry["last_seen"] = now
            known[digest] = entry
        pages[url] = {"variants": known}

        results.append({"url": url, "diff": diff, "record": record, "error": "",
                        "fresh": len(fresh), "variants": len(known)})

    checked_at = now
    save_snapshot({"version": 2, "checked_at": checked_at, "pages": pages},
                  config.BRAND_SNAPSHOT_PATH)
    path = write_review(results, config.BRAND_REVIEW_PATH, checked_at)

    # --- the other half: ask a person what the site cannot tell us ---------
    body = config.BRAND_CONTACT_BODY.format(
        changes=changes_paragraph(results),
        brand_file="BRAND.md", config_file="config.py",
        stamp=f"(sent by tools/brand_check.py, {checked_at})")

    to = os.environ.get("SEND_TO") or config.BRAND_CONTACT
    live = args.send
    # jotpsych.com is a real domain. Reaching it takes an explicit --force on
    # top of --send, so a cron line that grows a --send flag cannot quietly
    # start mailing a real inbox every month.
    if live and to == config.BRAND_CONTACT and not args.force:
        print(f"\n  ! refusing to email {to} without --force. "
              f"Set SEND_TO in .env to redirect, or pass --force if you mean it.")
        live = False

    senders = [send_mod.FileSender(outdir="logs")]
    if live:
        senders.append(send_mod.SMTPSender())
    row = {config.ID_FIELD: "brand_check"}
    for s in senders:
        try:
            print(f"[ask]      {s.send(to, config.BRAND_CONTACT_SUBJECT, body, row)}")
        except Exception as e:  # noqa: BLE001
            print(f"[ask]      {s.name} FAILED: {e}")

    material = sum(1 for r in results if r["record"]["severity"] == "material")
    print(f"\n--- brand check ---")
    print(f"  {len(results)} page(s) read, {material} materially changed")
    print(f"  work order -> {path}")
    print(f"  snapshot   -> {config.BRAND_SNAPSHOT_PATH}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

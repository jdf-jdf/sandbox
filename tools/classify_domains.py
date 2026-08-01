#!/usr/bin/env python3
"""
Research every .org / .edu domain in the intake list, once, and write the
verdicts to disk.

    python tools/classify_domains.py            # research what isn't cached
    python tools/classify_domains.py --dry      # list the work, call nothing
    python tools/classify_domains.py --refresh  # re-research everything
    python tools/classify_domains.py --domain med.cornell.edu

Why this is a separate script and not part of the run:

The machine's decision layer is supposed to be the part that cannot get
anything wrong. It is deterministic, it is offline, and running it twice on
the same input gives the same answer twice. Web search is none of those
things. Folding a search into decide.py would mean every run paid for network
calls, every run could produce a different answer, and a search outage would
change who gets contacted.

So the research is out of band and cached. It runs when the list changes, a
human can read the verdicts and overrule any of them by editing the JSON, and
the run itself never leaves the building.

The cost shape is per-domain, not per-row: 300 clinicians at 40 employers is
40 searches the first time and zero every time after.
"""
import argparse
import csv
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from run import load_dotenv  # noqa: E402
import config  # noqa: E402
from machine import domains, generate  # noqa: E402

# Newest first. The server-side search tool is versioned and an account that
# has not been enabled for a newer one gets a 400, which is recoverable: drop
# to the next version rather than failing the whole run.
WEB_SEARCH_VERSIONS = [
    "web_search_20260318",
    "web_search_20260209",
    "web_search_20250305",
]

RECORD_TOOL = {
    "name": "record_verdict",
    "description": "Record the final classification for the domain. Call once.",
    "input_schema": {
        "type": "object",
        "properties": {
            "organization": {
                "type": "string",
                "description": "The organization that owns the domain, as found.",
            },
            "verdict": {
                "type": "string",
                "enum": ["health_system", "training", "private_practice", "unclear"],
            },
            "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
            "why": {
                "type": "string",
                "description": "One or two sentences. What the search showed, "
                               "not what the name suggests.",
            },
            "sources": {
                "type": "array",
                "items": {"type": "string"},
                "description": "URLs that support the verdict.",
            },
        },
        "required": ["organization", "verdict", "confidence", "why", "sources"],
        "additionalProperties": False,
    },
}


def already_settled(email):
    """True if config already decides this address without research.

    @kp.org is named in INSTITUTIONAL_EMAIL_DOMAINS and @gmail.com in
    PERSONAL_EMAIL_DOMAINS. Paying a search to re-confirm either would be
    silly, and would quietly let the cache overrule a decision a human made
    on purpose.
    """
    probe = email.lower()
    named = (list(config.INSTITUTIONAL_EMAIL_DOMAINS)
             + list(config.PERSONAL_EMAIL_DOMAINS))
    return any(p.lower() in probe for p in named)


def domains_needing_research(path, cache, refresh=False):
    """Unique domains in the CSV that the machine cannot settle on its own."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Intake file not found: {path}")

    found = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            email = (row.get(config.ADDRESS_FIELD) or "").strip()
            if already_settled(email):
                continue
            domain = domains.domain_of(email)
            if not domains.needs_lookup(domain):
                continue
            if domain in cache and not refresh:
                continue
            found.setdefault(domain, []).append(
                (row.get(config.LABEL_FIELD) or "?").strip())
    return found


def _extract_verdict(content):
    for block in content:
        if getattr(block, "type", None) == "tool_use" and block.name == "record_verdict":
            return block.input
    return None


def research(client, domain, search_tool, attempts=3):
    """One domain, one verdict. Returns a record dict, always."""
    prompt = config.DOMAIN_RESEARCH_PROMPT.format(
        domain=domain, min_confidence=config.DOMAIN_MIN_CONFIDENCE_TO_CONTACT)
    messages = [{"role": "user", "content": prompt}]

    last_err = None
    for attempt in range(attempts):
        try:
            # The server runs the searches itself and can pause the turn
            # partway through a long one. Handing the assistant content back
            # unchanged resumes it; not handling this truncates the research
            # and looks like a confidently under-informed answer.
            for _ in range(6):
                resp = client.messages.create(
                    model=config.MODEL,
                    max_tokens=config.MAX_TOKENS,
                    thinking={"type": "adaptive"},
                    tools=[search_tool, RECORD_TOOL],
                    messages=messages,
                )
                verdict = _extract_verdict(resp.content)
                if verdict:
                    return {
                        "verdict": verdict.get("verdict", "unclear"),
                        "confidence": verdict.get("confidence", "low"),
                        "organization": verdict.get("organization", ""),
                        "why": verdict.get("why", ""),
                        "sources": verdict.get("sources", []),
                        "source": "llm+search",
                    }
                if resp.stop_reason != "pause_turn":
                    break
                messages.append({"role": "assistant", "content": resp.content})

            # Searched, then answered in prose instead of calling the tool.
            messages.append({"role": "assistant", "content": resp.content})
            messages.append({"role": "user",
                             "content": "Call record_verdict now with your conclusion."})
            continue
        except Exception as e:  # noqa: BLE001 -- one bad domain must not end the run
            last_err = e
            if attempt < attempts - 1:
                time.sleep(2 ** attempt)

    return {
        "verdict": "unclear",
        "confidence": "low",
        "organization": "",
        "why": f"research failed: {type(last_err).__name__}: {last_err}"
               if last_err else "model never returned a verdict",
        "sources": [],
        "source": "failed",
    }


def save(cache, path):
    """Write atomically. A half-written verdict file read by the next run
    would be worse than no verdict file at all."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"version": 1, "domains": cache}, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)


def pick_search_tool(client):
    """Return the newest search tool this account will accept."""
    for version in WEB_SEARCH_VERSIONS:
        tool = {"type": version, "name": "web_search",
                "max_uses": config.DOMAIN_MAX_SEARCHES}
        try:
            client.messages.create(
                model=config.MODEL, max_tokens=64, tools=[tool],
                messages=[{"role": "user", "content": "Reply with: ok"}],
            )
            return tool
        except Exception as e:  # noqa: BLE001
            # A rejected key looks identical to an unavailable tool version
            # from here, and reporting it as one sends the reader hunting
            # through their account settings for a problem that is in .env.
            if generate.is_auth_error(e):
                raise RuntimeError(
                    f"ANTHROPIC_API_KEY was rejected ({e}). Fix it in .env; "
                    f"`python tools/check_llm.py` tests it on its own.") from None
            print(f"  ({version} unavailable: {type(e).__name__})")
    raise RuntimeError("No usable web_search tool version for this account.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=config.INTAKE_CSV)
    ap.add_argument("--dry", action="store_true",
                    help="list the domains that need research, call nothing")
    ap.add_argument("--refresh", action="store_true",
                    help="re-research domains already in the cache")
    ap.add_argument("--domain", action="append", default=[],
                    help="research one domain, ignoring the CSV (repeatable)")
    args = ap.parse_args()

    load_dotenv()
    cache = dict(domains.load(force=True))

    if args.domain:
        work = {d.strip().lower(): ["(manual)"] for d in args.domain}
    else:
        work = domains_needing_research(args.input, cache, refresh=args.refresh)

    if not work:
        print(f"Nothing to research. {len(cache)} domain(s) already in "
              f"{config.DOMAIN_CACHE_PATH}.")
        return 0

    print(f"\n{len(work)} domain(s) need research:")
    for domain, people in sorted(work.items()):
        print(f"  {domain:<40} {len(people)} row(s): {', '.join(people[:3])}"
              f"{' ...' if len(people) > 3 else ''}")

    if args.dry:
        print("\n--dry: nothing called, nothing written.")
        return 0

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("\n! ANTHROPIC_API_KEY not set. Research needs the model and the "
              "web. Nothing written.")
        return 1
    try:
        import anthropic
    except ImportError:
        print("\n! SDK missing. Run: pip install -r requirements.txt")
        return 1

    client = anthropic.Anthropic()
    print()
    search_tool = pick_search_tool(client)
    print(f"using {search_tool['type']}, max {config.DOMAIN_MAX_SEARCHES} "
          f"searches per domain\n")

    for domain in sorted(work):
        record = research(client, domain, search_tool)
        cache[domain] = record
        save(cache, config.DOMAIN_CACHE_PATH)   # after each, so a crash keeps the work
        mark = {"health_system": "SKIP", "training": "trainee",
                "private_practice": "contact"}.get(record["verdict"], "REVIEW")
        print(f"  {domain:<40} {record['verdict']:<17} "
              f"{record['confidence']:<7} {mark}")
        if record["organization"]:
            print(f"  {'':<40} {record['organization']}")

    print(f"\nwrote {len(cache)} verdict(s) -> {config.DOMAIN_CACHE_PATH}")
    print("Read them. Anything wrong, edit the file: the run trusts it "
          "over the model.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Research the individual people the domain layer could only guess about, and
write the verdicts to disk.

    python tools/classify_people.py                  # research who isn't cached
    python tools/classify_people.py --dry            # list the work, call nothing
    python tools/classify_people.py --refresh-stale  # re-confirm expired titles
    python tools/classify_people.py --refresh        # re-research everyone

Why this exists as a second pass.

tools/classify_domains.py answers "what is this organization". That is enough
for a hospital, where the answer decides the person too: nobody at @kp.org is
buying an EHR add-on. It is not enough for a university. cornell.edu comes
back `training`, and `training` is a fact about the campus, not about the
clinician on it -- who may be a doctoral student, a postdoc, a counselling
centre clinician, a training director, or a professor of thirty years.

So the domain verdict is treated as a hypothesis and checked here, per person.

The cost shape is different from the domain pass and worth being honest
about. Domains amortise: 4,000 clinicians at 300 employers is 300 searches.
People do not. Every row is its own search, and there is no second row that
benefits from it. That is why this only runs for rows the domain layer parked
in config.PERSON_LOOKUP_SETTINGS -- the small slice where the guess is both
uncertain and expensive to get wrong -- and never for the whole list.

Titles expire. A verdict records the publication date of the evidence behind
it, and machine/people.py stops trusting one older than
config.PERSON_EVIDENCE_MAX_AGE_MONTHS. --refresh-stale re-researches exactly
those rather than paying for the whole file again.
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
from machine import domains, people  # noqa: E402

# Newest first. An account not enabled for a newer tool version gets a 400,
# which is recoverable: drop to the next rather than failing the whole run.
WEB_SEARCH_VERSIONS = [
    "web_search_20260318",
    "web_search_20260209",
    "web_search_20250305",
]

RECORD_TOOL = {
    "name": "record_person",
    "description": "Record the final classification for this person. Call once.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Their current role as stated by the source, "
                               "verbatim where possible.",
            },
            "credential": {
                "type": "string",
                "description": "Professional credential as found (MD, PsyD, "
                               "LCSW, LMFT...). Empty if the search did not "
                               "show one. Never inferred from a job title: "
                               "the machine routes on this.",
            },
            "verdict": {
                "type": "string",
                "enum": ["trainee", "faculty", "staff_clinician",
                         "private_practice", "unclear"],
            },
            "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
            "evidence_date": {
                "type": "string",
                "description": "When the supporting evidence was published or "
                               "last updated: YYYY-MM-DD, YYYY-MM, or YYYY. "
                               "The date of the SOURCE, never today's date.",
            },
            "why": {
                "type": "string",
                "description": "One or two sentences. What the search showed, "
                               "including how you dated it.",
            },
            "sources": {
                "type": "array",
                "items": {"type": "string"},
                "description": "URLs that support the verdict.",
            },
        },
        "required": ["title", "credential", "verdict", "confidence",
                     "evidence_date", "why", "sources"],
        "additionalProperties": False,
    },
}


def already_settled(email):
    """True if config decides this address without any research at all."""
    probe = (email or "").lower()
    named = (list(config.INSTITUTIONAL_EMAIL_DOMAINS)
             + list(config.PERSONAL_EMAIL_DOMAINS))
    return any(p.lower() in probe for p in named)


def people_needing_research(path, cache, refresh=False, refresh_stale=False,
                            include_simulated=False):
    """Rows whose setting is a domain-level guess this pass is meant to check.

    Returns (work, skipped_simulated).

    Deliberately re-derives the domain hypothesis rather than calling
    decide.route(), because route() already consults this cache: asking it
    would return "suppressed, never researched" and tell us nothing about
    which rows are worth researching.

    Seeded records are held back from --refresh on purpose. The sample list is
    invented, so researching "Tobias Grant at cornell.edu" returns an
    Australian reality-TV contestant and an unrelated LinkedIn profile, and
    the honest verdict is 'unclear' -- which then overwrites a deliberate
    fixture and pushes the row onto the human's work order. A reviewer running
    the documented command should not watch the sample decay. Pass
    --include-simulated to override, which is what a real list wants.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Intake file not found: {path}")

    work, skipped_simulated = [], []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            email = (row.get(config.ADDRESS_FIELD) or "").strip()
            label = (row.get(config.LABEL_FIELD) or "").strip()
            if not email or not label or already_settled(email):
                continue

            domain = domains.domain_of(email)
            if not domains.needs_lookup(domain):
                continue

            setting = domains.resolve(domain, config.DEFAULT_SETTING)["setting"]
            if not people.needs_lookup(setting):
                continue

            record = cache.get(people.key(email))
            if (record is not None
                    and record.get("source") == config.SIMULATED_SOURCE
                    and not include_simulated):
                skipped_simulated.append(label)
                continue

            if record is not None and not refresh:
                if not refresh_stale:
                    continue
                age = people.months_since(record.get("evidence_date", ""))
                if age is not None and age <= config.PERSON_EVIDENCE_MAX_AGE_MONTHS:
                    continue

            work.append({
                "email": email,
                "label": label,
                "domain": domain,
                "hypothesis": setting,
                "credential": (row.get("credential") or "").strip(),
            })
    return work, skipped_simulated


def _extract(content):
    for block in content:
        if getattr(block, "type", None) == "tool_use" and block.name == "record_person":
            return block.input
    return None


def research(client, person, search_tool, attempts=3):
    """One person, one verdict. Returns a record dict, always."""
    prompt = config.PERSON_RESEARCH_PROMPT.format(
        name=person["label"],
        domain=person["domain"],
        credential=person["credential"] or "(not recorded)",
        hypothesis=person["hypothesis"],
        max_age_months=config.PERSON_EVIDENCE_MAX_AGE_MONTHS,
        min_confidence=config.PERSON_MIN_CONFIDENCE_TO_CONTACT,
    )
    messages = [{"role": "user", "content": prompt}]

    last_err = None
    for attempt in range(attempts):
        try:
            # The server runs the searches itself and can pause the turn
            # partway through. Handing the assistant content back unchanged
            # resumes it; not handling this truncates the research and looks
            # like a confidently under-informed answer.
            for _ in range(6):
                resp = client.messages.create(
                    model=config.MODEL,
                    max_tokens=config.MAX_TOKENS,
                    thinking={"type": "adaptive"},
                    tools=[search_tool, RECORD_TOOL],
                    messages=messages,
                )
                found = _extract(resp.content)
                if found:
                    return {
                        "verdict": found.get("verdict", "unclear"),
                        "confidence": found.get("confidence", "low"),
                        "title": found.get("title", ""),
                        "credential": found.get("credential", ""),
                        "evidence_date": found.get("evidence_date", ""),
                        "why": found.get("why", ""),
                        "sources": found.get("sources", []),
                        "name": person["label"],
                        "domain": person["domain"],
                        "source": "llm+search",
                    }
                if resp.stop_reason != "pause_turn":
                    break
                messages.append({"role": "assistant", "content": resp.content})

            messages.append({"role": "assistant", "content": resp.content})
            messages.append({"role": "user",
                             "content": "Call record_person now with your conclusion."})
            continue
        except Exception as e:  # noqa: BLE001 -- one bad row must not end the run
            last_err = e
            if attempt < attempts - 1:
                time.sleep(2 ** attempt)

    return {
        "verdict": "unclear",
        "confidence": "low",
        "title": "",
        "credential": "",
        "evidence_date": "",
        "why": f"research failed: {type(last_err).__name__}: {last_err}"
               if last_err else "model never returned a verdict",
        "sources": [],
        "name": person["label"],
        "domain": person["domain"],
        "source": "failed",
    }


def save(cache, path):
    """Write atomically. A half-written verdict file read by the next run
    would be worse than no verdict file at all."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"version": 1, "people": cache}, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)


def pick_search_tool(client):
    """Return the newest search tool this account will accept."""
    for version in WEB_SEARCH_VERSIONS:
        tool = {"type": version, "name": "web_search",
                "max_uses": config.PERSON_MAX_SEARCHES}
        try:
            client.messages.create(
                model=config.MODEL, max_tokens=64, tools=[tool],
                messages=[{"role": "user", "content": "Reply with: ok"}],
            )
            return tool
        except Exception as e:  # noqa: BLE001
            print(f"  ({version} unavailable: {type(e).__name__})")
    raise RuntimeError("No usable web_search tool version for this account.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=config.INTAKE_CSV)
    ap.add_argument("--dry", action="store_true",
                    help="list who needs research, call nothing")
    ap.add_argument("--refresh", action="store_true",
                    help="re-research everyone already cached")
    ap.add_argument("--refresh-stale", action="store_true",
                    help="re-research only those whose evidence has expired")
    ap.add_argument("--include-simulated", action="store_true",
                    help="also re-research seeded sample records (on the "
                         "invented list this replaces them with 'unclear')")
    args = ap.parse_args()

    load_dotenv()
    cache = dict(people.load(force=True))
    work, skipped = people_needing_research(
        args.input, cache, refresh=args.refresh,
        refresh_stale=args.refresh_stale,
        include_simulated=args.include_simulated)

    if skipped:
        print(f"\nholding {len(skipped)} seeded sample record(s): "
              f"{', '.join(skipped[:4])}{' ...' if len(skipped) > 4 else ''}")
        print("  These people are invented, so there is nothing on the web to "
              "find and\n  researching them would replace a deliberate fixture "
              "with 'unclear'.\n  Use --include-simulated on a real list.")

    if not work:
        print(f"Nobody to research. {len(cache)} person/people already in "
              f"{config.PERSON_CACHE_PATH}.")
        return 0

    print(f"\n{len(work)} person/people need research "
          f"(domain said {', '.join(sorted({p['hypothesis'] for p in work}))}):")
    for p in work:
        print(f"  {p['label']:<24} {p['credential']:<12} @{p['domain']}")

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
    print(f"using {search_tool['type']}, max {config.PERSON_MAX_SEARCHES} "
          f"searches per person\n")

    for p in work:
        record = research(client, p, search_tool)
        cache[people.key(p["email"])] = record
        save(cache, config.PERSON_CACHE_PATH)  # after each, so a crash keeps the work
        age = people.months_since(record["evidence_date"])
        stamp = f"{age}mo" if age is not None else "undated"
        mark = {"trainee": "contact", "private_practice": "contact"}.get(
            record["verdict"], "SKIP" if record["verdict"] != "unclear" else "REVIEW")
        print(f"  {p['label']:<24} {record['verdict']:<16} "
              f"{record['confidence']:<7} {stamp:<8} {mark}")
        if record["title"]:
            print(f"  {'':<24} {record['title']}")

    print(f"\nwrote {len(cache)} verdict(s) -> {config.PERSON_CACHE_PATH}")
    print("Read them. Anything wrong, edit the file: the run trusts it "
          "over the model.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

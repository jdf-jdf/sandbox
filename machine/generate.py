"""
GENERATION -- the LLM call, wrapped so it cannot take the machine down.

Two things matter here under a clock:
  1. Retries, so one flaky call doesn't kill a run.
  2. A template fallback, so the loop still CLOSES if the API is down or you
     ran out of credit. A closed loop on fallback text scores; a broken run
     scores nothing. You can always say "LLM path stubbed" in the README.
"""
import os
import time

import config

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        import anthropic
    except ImportError:
        return None
    _client = anthropic.Anthropic(api_key=key)
    return _client


def _fallback(row, decision):
    """Deterministic template. Not good writing -- it exists so the loop
    never breaks. If you see this in out/, your API path failed.

    Note it echoes the `notes` column straight into the body. That is
    deliberate: it is exactly the naive behaviour the QC gate exists to
    catch, so a no-API-key run still demonstrates the gate firing on the
    seeded rows instead of producing a suspiciously clean log.
    """
    return (
        f"Hi {row['name']},\n\n"
        f"[FALLBACK TEMPLATE -- LLM unavailable at generation time]\n\n"
        f"You're a {row['credential']} working in {row['practice_type']}. "
        f"Documentation is the part of that work that follows you home. "
        f"JotPsych writes the note from the session so the evening is yours.\n\n"
        f"What we have on file: {row.get('notes', '') or '(nothing)'}\n\n"
        f"-- \n"
    )


def draft(row, decision, learned_constraints, attempts=3):
    """Return (text, source) where source is 'llm' or 'fallback'."""
    client = _get_client()
    if client is None:
        return _fallback(row, decision), "fallback"

    constraint_block = ""
    if learned_constraints:
        constraint_block = (
            "Additionally, previous runs of this machine were rejected for "
            "using the following. Never use them:\n"
            + "\n".join(f"- {c}" for c in learned_constraints)
        )

    prompt = config.PROMPT.format(
        name=row["name"],
        credential=row["credential"],
        practice_type=row["practice_type"],
        segment=decision["segment"],
        notes=row.get("notes", "") or "(nothing on file)",
        segment_brief=config.SEGMENT_BRIEF.get(decision["segment"], ""),
        learned_constraints=constraint_block,
    )

    last_err = None
    for i in range(attempts):
        try:
            resp = client.messages.create(
                model=config.MODEL,
                max_tokens=config.MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.content[0].text.strip(), "llm"
        except Exception as e:          # noqa: BLE001 -- deliberately broad
            last_err = e
            if i < attempts - 1:
                time.sleep(2 ** i)

    print(f"  ! LLM failed after {attempts} attempts ({last_err}); using fallback")
    return _fallback(row, decision), "fallback"

"""
FOLLOW-UP -- the email a reply earns.

tools/classify_replies.py decides WHAT a reply meant. This module decides
WHAT WE SAY BACK, keyed off config.LEAD_TEMPERATURE: a hot lead who asked a
direct question gets a different email than a warm lead who is a year from
opening a practice, even though both are, technically, "a reply that got
read."

Generation is thin here for the same reason it is thin in
machine/generate.py: the model writes prose, config decides register, and the
QC gate is the only thing standing between a draft and an inbox either way.
This module does not call qc.check() itself -- tools/followup.py does,
exactly the way run.py gates the first email -- so a follow-up drafted here
is not sent-implied until the same 23 rules have read it.
"""
import time

import config
from machine import generate


def temperature_for(disposition):
    """Lead temperature for a disposition, or None if it earns no follow-up
    at all (see config.LEAD_TEMPERATURE: not_interested is the one case)."""
    return config.LEAD_TEMPERATURE.get(disposition)


def _fallback(clinician, verdict, temperature):
    """Deterministic template, same purpose as generate._fallback: the loop
    must not break when the model is unavailable, even for a second email."""
    return (
        f"Hi {clinician.get('name') or 'there'},\n\n"
        f"[FALLBACK TEMPLATE -- LLM unavailable at generation time]\n\n"
        f"Thanks for writing back. We read it as: "
        f"{verdict.get('why') or '(no detail on file)'}\n"
        f"({temperature} lead, disposition: "
        f"{verdict.get('disposition', 'unclear')})\n"
    )


def draft(clinician, verdict, learned_constraints=None, attempts=3):
    """Return (text, source, temperature) for one classified reply, or
    (None, None, None) if the disposition earns no follow-up at all.

    `clinician` carries at least name/segment/setting, recovered from the
    attribution ledger by tools/followup.py -- the same shape
    generate.draft() already expects a row to carry, so the two share a
    prompt-formatting approach rather than inventing a second one.

    Reaches into machine.generate for its client/error-handling helpers
    rather than re-instantiating an SDK client here: a second email is not a
    second set of rules for what counts as a rejected credential.
    """
    disposition = verdict.get("disposition", "unclear")
    temperature = temperature_for(disposition)
    if temperature is None:
        return None, None, None

    client = generate._get_client()  # noqa: SLF001 -- shared client, see docstring
    if client is None:
        return _fallback(clinician, verdict, temperature), "fallback", temperature

    constraint_block = ""
    if learned_constraints:
        constraint_block = (
            "Additionally, previous runs of this machine were rejected for "
            "using the following. Never use them:\n"
            + "\n".join(f"- {c}" for c in learned_constraints)
        )

    prompt = config.FOLLOWUP_PROMPT.format(
        brand_brief=config.BRAND_BRIEF,
        name=clinician.get("name") or "there",
        segment=clinician.get("segment") or "unspecified",
        setting=clinician.get("setting") or "unknown",
        reply_text=verdict.get("reply_text", ""),
        reply_disposition=disposition,
        temperature=temperature,
        followup_brief=config.FOLLOWUP_BRIEF.get(temperature, ""),
        learned_constraints=constraint_block,
    )

    last_err = None
    for i in range(attempts):
        try:
            resp = client.messages.create(
                model=config.MODEL,
                max_tokens=config.MAX_TOKENS,
                thinking={"type": "adaptive"},
                output_config={"effort": config.EFFORT},
                messages=[{"role": "user", "content": prompt}],
            )
            if resp.stop_reason == "refusal":
                return (_fallback(clinician, verdict, temperature),
                        "fallback", temperature)
            text = next((b.text for b in resp.content if b.type == "text"), "")
            if not text.strip():
                raise ValueError("model returned no text block")
            return text.strip(), "llm", temperature
        except Exception as e:          # noqa: BLE001 -- deliberately broad
            if generate.is_auth_error(e):
                raise generate.CredentialError(str(e)) from None
            last_err = e
            if i < attempts - 1:
                time.sleep(2 ** i)

    print(f"  ! LLM failed after {attempts} attempts ({last_err}); using fallback")
    return _fallback(clinician, verdict, temperature), "fallback", temperature

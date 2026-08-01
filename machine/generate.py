"""
GENERATION -- the model call, wrapped so it cannot take the machine down.

Two defences, because an outage here should degrade the output rather than
stop the loop:
  1. Retries with backoff, so one flaky call doesn't kill a run.
  2. A template fallback, so the machine still completes its cycle when the
     API is unreachable. Degraded text that ships beats no text at all, and
     the run log makes it obvious which path produced each draft.

Both defences are for a TRANSIENT failure. A rejected credential is not one,
and treating it as one is actively misleading: every row retries three times,
falls back to the template, and the template echoes the raw row -- including
the mobile number -- so the gate blocks all of it. The run then reports a wall
of `phone_number` violations, which describes neither the cause nor the fix.
So an auth failure stops the run instead, once, saying what is wrong.
"""
import os
import time

import config

_client = None


class CredentialError(RuntimeError):
    """The API key was rejected. Not retryable, and not a per-row problem."""


def is_auth_error(exc):
    """True for the errors no amount of retrying will fix.

    Checked by status code and class name rather than isinstance, because the
    SDK is imported lazily and may not be importable in this scope at all.
    """
    if getattr(exc, "status_code", None) in (401, 403):
        return True
    return type(exc).__name__ in ("AuthenticationError", "PermissionDeniedError")


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
    """Deterministic template. Not good writing: it exists so the loop never
    breaks. Its presence in out/ means the model path failed for that row.

    It echoes the raw intake fields straight into the body, which is the
    naive behaviour the QC gate exists to catch. That is deliberate -- the
    degraded path is held to the same gate as the good one, and trips it.
    """
    # Reads the row generically. The safety net must not itself depend on the
    # clinician schema, or it breaks in exactly the situation it exists for.
    label = row.get(config.LABEL_FIELD, "there")
    detail = ", ".join(
        f"{k}: {v}" for k, v in row.items()
        if v and not k.startswith("_") and k not in
        (config.ID_FIELD, config.LABEL_FIELD, config.ADDRESS_FIELD)
    )
    return (
        f"Hi {label},\n\n"
        f"[FALLBACK TEMPLATE -- LLM unavailable at generation time]\n\n"
        f"Paperwork is the part of the work that follows you home. "
        f"JotPsych writes the chart during the session and checks the claim "
        f"before it goes out.\n\n"
        f"What we have on file: {detail or '(nothing)'}\n"
    )


def _claim_block():
    """config.APPROVED_CLAIMS, as the prompt sees it.

    The source URL travels with each claim rather than being stripped out. It
    is not for the reader, since nobody cites a footnote in a cold email. It
    is there so the model can see that every line is a quotation of something
    already published, which is the entire basis on which it is allowed to
    use one at all.
    """
    if not config.APPROVED_CLAIMS:
        return ""
    lines = "\n".join(f'- "{claim}"  (published: {source})'
                      for claim, source in config.APPROVED_CLAIMS)
    return "Claims you may quote, word for word and no other way:\n" + lines


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

    # Format against the WHOLE row rather than a hand-listed set of fields, so
    # adding a column to the CSV and referencing it in config.PROMPT needs no
    # change here.
    fields = dict(row)
    # An empty optional cell reads better to the model as an explicit absence
    # than as a blank hole. Required fields are never empty (intake rejects
    # those rows), so this only ever touches optional ones.
    for k, v in fields.items():
        if not v and k not in config.REQUIRED_COLUMNS:
            fields[k] = config.MISSING_FIELD_DEFAULTS.get(k, "(nothing on file)")
    # Per-field wording matters more than it looks: "(nothing on file)" under
    # Credential reads like an empty notes field, while "(not known)" reads as
    # a fact about our knowledge. The model treats the second as a boundary and
    # the first as an invitation.

    # Derived, not carried: the last four digits of the mobile, so copy can
    # name the number a reply would come from without printing the whole thing
    # in an email that may be forwarded.
    # The absent case is a WORD, not an empty string. Interpolating "" turned
    # the prompt's own example into "the number ending ?", and the model
    # dutifully copied the broken shape into the email. A placeholder that
    # cannot be mistaken for a value cannot be echoed as one.
    digits = "".join(c for c in str(row.get(config.MOBILE_FIELD, "")) if c.isdigit())
    fields["mobile_last4"] = digits[-4:] if len(digits) >= 4 else "NONE-ON-FILE"

    setting = decision.get("setting", "")

    # Membership of BRAND_NEWS_BY_SETTING is the gate on whether this person
    # hears what the product does now. Absent means suppressed, which is the
    # safe direction: a setting nobody has written copy for yet gets silence
    # rather than whatever sales pitch happened to be nearest.
    sells = setting in config.BRAND_NEWS_BY_SETTING

    fields.update({
        "segment": decision["segment"],
        "segment_brief": config.SEGMENT_BRIEF.get(decision["segment"], ""),
        "setting": setting,
        "setting_brief": config.SETTING_BRIEF.get(setting, ""),
        "brand_brief": config.BRAND_BRIEF,
        "brand_news": config.BRAND_NEWS_BY_SETTING.get(
            setting, config.BRAND_NEWS_SUPPRESSED),
        # Claims travel with the news or not at all. A statistic in an email
        # to somebody we just decided not to pitch is still a pitch.
        "approved_claims": _claim_block() if sells else "",
        "learned_constraints": constraint_block,
    })

    try:
        prompt = config.PROMPT.format(**fields)
    except KeyError as e:
        # Fail loud and name the column. A silent half-filled prompt is much
        # worse than stopping here.
        raise KeyError(
            f"config.PROMPT references {{{e.args[0]}}} but the intake row has "
            f"no such column. Row has: {sorted(row)}"
        ) from None

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

            # The model can decline a request outright. That returns a normal
            # 200 with an empty/partial body, so check before reading content
            # or you get a confusing IndexError instead of a clear reason.
            if resp.stop_reason == "refusal":
                print(f"  ! model declined to draft for {row.get(config.LABEL_FIELD, '?')}")
                return _fallback(row, decision), "fallback"

            # With thinking on, content[0] is a thinking block, not text, so
            # resp.content[0].text raises AttributeError. Find the text block.
            text = next((b.text for b in resp.content if b.type == "text"), "")
            if not text.strip():
                raise ValueError("model returned no text block")

            return text.strip(), "llm"
        except Exception as e:          # noqa: BLE001 -- deliberately broad
            if is_auth_error(e):
                raise CredentialError(str(e)) from None
            last_err = e
            if i < attempts - 1:
                time.sleep(2 ** i)

    print(f"  ! LLM failed after {attempts} attempts ({last_err}); using fallback")
    return _fallback(row, decision), "fallback"

#!/usr/bin/env python3
"""
THE MACHINE. One entrypoint, one pass, the whole loop.

  intake (a file it did not author)
    -> decide (on its own, deterministically)
      -> generate
        -> QC gate (refuses to send what is off-brand)
          -> outbound (file on disk + a real email)
            -> state (measures itself, and constrains the next cycle)

Usage:
  python run.py              # dry: writes to out/, sends no email
  python run.py --send       # live: also emails via Gmail SMTP
  python run.py --input other.csv
"""
import argparse
import datetime
import json
import os
import sys

import config
from machine import (attribution, decide, generate, intake, people, qc, review,
                     send, signature, state as state_mod)


def load_dotenv(path=".env"):
    """Tiny .env loader, so reading config needs no third-party dependency."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def brand_age_warning():
    """Say so when the brand facts are older than the brand.

    The machine writes in JotPsych's voice from constants in config.py, and
    those constants were wrong for two years without anything noticing. This
    is the noticing. It warns and returns: a snapshot that is five weeks old
    is a reason to run tools/brand_check.py, not a reason to send nobody
    anything today, and a gate that stops the run over a stale JSON file is a
    gate somebody deletes.
    """
    path = config.BRAND_SNAPSHOT_PATH
    if not os.path.exists(path):
        return (f"no brand snapshot at {path}. Run tools/brand_check.py to "
                f"record what the site says today.")
    try:
        with open(path, encoding="utf-8") as f:
            checked = json.load(f).get("checked_at")
        age = (datetime.datetime.now()
               - datetime.datetime.fromisoformat(checked)).days
    except (ValueError, TypeError, json.JSONDecodeError) as e:
        return f"could not read {path} ({type(e).__name__}); brand age unknown."
    if age > config.BRAND_MAX_AGE_DAYS:
        return (f"brand snapshot is {age} days old (limit "
                f"{config.BRAND_MAX_AGE_DAYS}). The product may have moved. "
                f"Run tools/brand_check.py.")
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--send", action="store_true",
                    help="actually email via SMTP (default: files only)")
    ap.add_argument("--input", default=config.INTAKE_CSV,
                    help="intake CSV; swap this to change the outputs")
    args = ap.parse_args()

    load_dotenv()
    os.makedirs("quarantine", exist_ok=True)

    st = state_mod.load()
    learned = state_mod.learned_constraints(st)

    run_no = len(st.get("runs", [])) + 1
    print(f"\n=== run {run_no} "
          f"| input: {args.input} "
          f"| mode: {'LIVE SEND' if args.send else 'dry'} ===")
    stale = brand_age_warning()
    if stale:
        print(f"! {stale}")
    if learned:
        print(f"carrying {len(learned)} learned constraint(s) from previous runs:")
        for c in learned:
            print(f"  - never write {c!r}")
    print()

    # --- 1. INTAKE -------------------------------------------------------
    rows, bad_rows = intake.read_rows(args.input, config.REQUIRED_COLUMNS)
    print(f"[intake]   {len(rows)} usable, {len(bad_rows)} rejected at the door")
    for b in bad_rows:
        print(f"           line {b['_line']}: {b['_reason']}")

    try:
        senders = send.build_senders(live=args.send)
    except RuntimeError as e:
        print(f"\n! {e}\n")
        return 1

    # The signature reaches inboxes without passing the per-draft gate, so it
    # is held to the same rules here instead. Once, before anything is sent.
    sig_violations = signature.check()
    if any(v["severity"] == "block" for v in sig_violations):
        print("\n! config.SIGNATURE trips the refusal rules:")
        for v in sig_violations:
            print(f"    {v['severity']:<5} {v['rule']}: {v['evidence']!r}")
        print("  Fix the signature in config.py. Nothing was sent.\n")
        return 1
    for v in sig_violations:
        print(f"[signature] flag {v['rule']}: {v['evidence']!r}")

    quarantined, flagged, suppressed, sent_ok = [], [], [], []
    all_violations = []

    for row in rows:
        # --- 2. DECIDE ---------------------------------------------------
        # Top the row up from the researched cache before anything reads it,
        # so routing, the prompt and the gate all see one row. The real export
        # is name/email/mobile; everything else was found, not given.
        row = people.enrich(row)
        label = row.get(config.LABEL_FIELD, row[config.ID_FIELD])
        decision = decide.route(row)
        if not decision["should_contact"]:
            suppressed.append({"row": row, "decision": decision})
            print(f"[decide]   {label:<24} SKIP  {decision['reason']}")
            continue

        # --- 3. GENERATE -------------------------------------------------
        text, source = generate.draft(row, decision, learned)

        # --- 4. QC GATE --------------------------------------------------
        blocked, violations = qc.check(text, row, decision)
        all_violations.extend(violations)

        if blocked:
            with open(f"quarantine/{row[config.ID_FIELD]}.txt", "w", encoding="utf-8") as f:
                f.write(text)
            quarantined.append({"row": row, "violations": violations, "text": text})
            names = ", ".join(v["rule"] for v in violations if v["severity"] == "block")
            print(f"[QC]       {label:<24} BLOCK {names}")
            continue

        if violations:
            flagged.append({"row": row, "violations": violations})

        # --- 5. OUTBOUND -------------------------------------------------
        try:
            subject = config.SUBJECT_TEMPLATE.format(**row)
        except KeyError as e:
            print(f"! config.SUBJECT_TEMPLATE references {{{e.args[0]}}}, "
                  f"which is not a column in {args.input}. Row has: {sorted(row)}")
            return 1
        to = os.environ.get("SEND_TO") or row[config.ADDRESS_FIELD]

        # Stamped after the gate, never before: the gate judges the copy, and
        # a tracking link the model might reword is not a tracking link.
        tok = attribution.token(row, run_no)
        text = attribution.stamp(text, tok)

        # Signed last, because the signature is the bottom of the email. Any
        # further post-gate append belongs above this line, not below it.
        text = signature.stamp(text)

        results = []
        for s in senders:
            try:
                results.append(s.send(to, subject, text, row,
                                      reply_to=attribution.reply_to(tok)))
            except Exception as e:  # noqa: BLE001
                results.append(f"{s.name} FAILED: {e}")
        attribution.record(row, decision, run_no, tok, results)
        sent_ok.append(row)
        flag = " (flagged)" if violations else ""
        print(f"[send]     {label:<24} OK    {'; '.join(results)}{flag} [{source}]")

    # --- 6. STATE / LEARNING --------------------------------------------
    metrics = {
        "input": args.input,
        "read": len(rows) + len(bad_rows),
        "intake_rejected": len(bad_rows),
        "suppressed": len(suppressed),
        "generated": len(rows) - len(suppressed),
        "blocked": len(quarantined),
        "flagged": len(flagged),
        "sent": len(sent_ok),
        "live": bool(args.send),
    }
    st = state_mod.record_run(st, metrics, all_violations)
    state_mod.save(st)

    log_path = review.append_rejects_log(quarantined)
    queue_path = review.write_queue(quarantined, flagged, suppressed, bad_rows)

    print(f"\n--- summary ---")
    print(f"  read {metrics['read']}  ->  sent {metrics['sent']}  "
          f"(blocked {metrics['blocked']}, suppressed {metrics['suppressed']}, "
          f"bad data {metrics['intake_rejected']})")
    print(f"\nrejection rate by run:")
    print(state_mod.trend(st))
    print(f"\n  evidence -> {log_path}")
    print(f"  human work order -> {queue_path}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())

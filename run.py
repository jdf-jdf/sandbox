#!/usr/bin/env python3
"""
THE MACHINE. One entrypoint, one pass, the whole loop.

  intake (a file it did not author)
    -> decide (on its own, deterministically)
      -> generate
        -> QC gate (refuses to send what is off-brand)
          -> outbound (file on disk + a real email)
            -> state (measures itself, and improves next cycle)

Usage:
  python run.py              # dry: writes to out/, sends no email
  python run.py --send       # live: also emails via Gmail SMTP
  python run.py --input other.csv
"""
import argparse
import os
import sys

import config
from machine import decide, generate, intake, qc, review, send, state as state_mod


def load_dotenv(path=".env"):
    """Tiny .env loader so there's no dependency to install tomorrow."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--send", action="store_true",
                    help="actually email via SMTP (default: files only)")
    ap.add_argument("--input", default=config.INTAKE_CSV,
                    help="intake CSV -- swap this to change the outputs")
    args = ap.parse_args()

    load_dotenv()
    os.makedirs("quarantine", exist_ok=True)

    st = state_mod.load()
    learned = state_mod.learned_constraints(st)

    print(f"\n=== run {len(st.get('runs', [])) + 1} "
          f"| input: {args.input} "
          f"| mode: {'LIVE SEND' if args.send else 'dry'} ===")
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

    quarantined, flagged, suppressed, sent_ok = [], [], [], []
    all_violations = []

    for row in rows:
        # --- 2. DECIDE ---------------------------------------------------
        decision = decide.route(row)
        if not decision["should_contact"]:
            suppressed.append({"row": row, "decision": decision})
            print(f"[decide]   {row['name']:<24} SKIP  {decision['reason']}")
            continue

        # --- 3. GENERATE -------------------------------------------------
        text, source = generate.draft(row, decision, learned)

        # --- 4. QC GATE --------------------------------------------------
        blocked, violations = qc.check(text, row, decision)
        all_violations.extend(violations)

        if blocked:
            with open(f"quarantine/{row['id']}.txt", "w", encoding="utf-8") as f:
                f.write(text)
            quarantined.append({"row": row, "violations": violations, "text": text})
            names = ", ".join(v["rule"] for v in violations if v["severity"] == "block")
            print(f"[QC]       {row['name']:<24} BLOCK {names}")
            continue

        if violations:
            flagged.append({"row": row, "violations": violations})

        # --- 5. OUTBOUND -------------------------------------------------
        subject = config.SUBJECT_TEMPLATE.format(**row)
        to = os.environ.get("SEND_TO") or row["email"]
        results = []
        for s in senders:
            try:
                results.append(s.send(to, subject, text, row))
            except Exception as e:  # noqa: BLE001
                results.append(f"{s.name} FAILED: {e}")
        sent_ok.append(row)
        flag = " (flagged)" if violations else ""
        print(f"[send]     {row['name']:<24} OK    {'; '.join(results)}{flag} [{source}]")

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

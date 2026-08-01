#!/usr/bin/env python3
"""
Draft the follow-up a classified reply earns.

    python tools/followup.py            # draft follow-ups for new verdicts
    python tools/followup.py --dry      # list the work, call nothing
    python tools/followup.py --refresh  # redraft everyone already done

tools/classify_replies.py decides WHAT a reply meant, and machine/replies.py
feeds that back into the NEXT scheduled win-back email's routing. This is the
other half: a reply is worth answering on its own thread, not just folded
into whatever run.py's cron does next. A hot lead who asked about pricing
should not wait for next month's scheduled run to hear back.

STUBBED FOR THIS DEMO, same shape as the rest of the reply-learning pipeline.
This drafts ONE follow-up per classified reply and writes it to
out/followup/<id>.txt, exactly like a dry run of run.py writes to out/. It
does not send anything and it does not schedule anything -- a real send path
and a real cadence (what happens if THIS goes unanswered too) is Week Two,
same boundary the rest of the machine draws around itself. What is NOT
stubbed: every draft here passes through the same QC gate and the same
refusal rules as the first email, via machine/qc.py. A follow-up earns no
less scrutiny for being the second email in the thread.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from run import load_dotenv  # noqa: E402
import config  # noqa: E402
from machine import attribution, followup, generate, qc  # noqa: E402
from machine import state as state_mod  # noqa: E402


def _clinician_for(clinician_id, ledger):
    """Recover name/segment/setting for a reply verdict from the send that
    earned it, newest run first. The reply cache only stores what the reply
    itself said; everything about the person still lives in the ledger."""
    for entry in reversed(ledger):
        if entry["id"] == clinician_id:
            return {"name": entry.get("name", ""),
                    "segment": entry.get("segment", ""),
                    "setting": entry.get("setting", "")}
    return {"name": clinician_id, "segment": "", "setting": ""}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true",
                    help="show who would get a follow-up, write nothing")
    ap.add_argument("--refresh", action="store_true",
                    help="redraft follow-ups already written")
    args = ap.parse_args()

    load_dotenv()

    if not os.path.exists(config.REPLY_CACHE_PATH):
        print(f"\nNo reply verdicts at {config.REPLY_CACHE_PATH}. Run "
              f"tools/classify_replies.py first.\n")
        return 0

    with open(config.REPLY_CACHE_PATH, encoding="utf-8") as f:
        verdicts = json.load(f).get("people", {})
    ledger = attribution.load_ledger()

    work, skipped = [], []
    for clinician_id, verdict in verdicts.items():
        temperature = followup.temperature_for(verdict.get("disposition", "unclear"))
        out_path = f"out/followup/{clinician_id}.txt"
        if temperature is None:
            skipped.append((clinician_id, "not_interested -- no follow-up, "
                            "honoring the opt-out"))
            continue
        if os.path.exists(out_path) and not args.refresh:
            continue
        work.append((clinician_id, verdict, temperature, out_path))

    if skipped:
        print(f"{len(skipped)} reply/replies earn no follow-up:")
        for cid, why in skipped:
            print(f"  {cid:<7} {why}")

    if not work:
        print(f"\nNothing new to draft. {len(verdicts)} verdict(s) in "
              f"{config.REPLY_CACHE_PATH}.")
        return 0

    print(f"\n{len(work)} follow-up(s) to draft:")
    for cid, verdict, temperature, _ in work:
        print(f"  {cid:<7} {temperature:<5} {verdict.get('disposition', '?')}")

    if args.dry:
        print("\n--dry: nothing called, nothing written.")
        return 0

    os.makedirs("out/followup", exist_ok=True)
    os.makedirs("quarantine", exist_ok=True)

    st = state_mod.load()
    learned = state_mod.learned_constraints(st)
    blocked_count = 0

    print()
    for clinician_id, verdict, temperature, out_path in work:
        clinician = _clinician_for(clinician_id, ledger)
        try:
            text, source, _ = followup.draft(clinician, verdict, learned)
        except generate.CredentialError as e:
            print(f"\n! ANTHROPIC_API_KEY was rejected: {e}\n")
            return 1

        row = {config.ID_FIELD: clinician_id, config.LABEL_FIELD: clinician["name"]}
        blocked, violations = qc.check(text, row)
        if blocked:
            blocked_count += 1
            quarantine_path = f"quarantine/followup-{clinician_id}.txt"
            with open(quarantine_path, "w", encoding="utf-8") as f:
                f.write(text)
            names = ", ".join(v["rule"] for v in violations if v["severity"] == "block")
            print(f"  {clinician_id:<7} {temperature:<5} BLOCK {names} "
                  f"-> {quarantine_path}")
            continue

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text)
        flag = " (flagged)" if violations else ""
        print(f"  {clinician_id:<7} {temperature:<5} OK{flag} -> {out_path} [{source}]")

    print(f"\nwrote {len(work) - blocked_count} follow-up draft(s) to "
          f"out/followup/, {blocked_count} blocked by the gate.")
    print("Nothing sent: this stub drafts and gates, it does not deliver. "
          "Wire machine/send.py to make it live.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

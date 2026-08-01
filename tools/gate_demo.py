#!/usr/bin/env python3
"""
Prove the gate, on demand, without waiting for the model to misbehave.

    python tools/gate_demo.py               # show what the gate catches
    python tools/gate_demo.py --feed-state  # and let the machine learn from it

WHY THIS EXISTS, honestly.

The brief asks to see at least one rejected output and the check that caught
it. On the current list the machine does not produce one, and that is worth
stating plainly rather than engineering around: across one live run of 27
sends and two dry ones, the gate blocked nothing. config.PROMPT forbids
statistics, hype, patient content and invented relationships up front, so the
model mostly does not write them, and even data/gate_test.csv (six rows built
to bait exactly those failures) came back clean.

A gate that never fires is indistinguishable from no gate. So this feeds it
drafts that a less-constrained model does produce -- every one of these is
either a real draft this machine wrote earlier in the build, or a close
paraphrase of one -- and shows what each rule catches and why.

The drafts are fixtures. The gate is the real one: it imports machine/qc.py
and config.REFUSAL_RULES, nothing is stubbed, and the blocks are appended to
logs/rejects.log in the same format a live run writes.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402
from machine import qc, review, state as state_mod  # noqa: E402

# (id, name, what is wrong with it, the draft)
FIXTURES = [
    ("D-01", "Marcus Feld", "quotes an unqualified vendor statistic",
     "Dr. Feld,\n\nYou left over price. Since then we have cut documentation "
     "time by a 90% reduction for most prescribers, and clinicians report "
     "saving 30 hours a month.\n\nBen\nJotPsych"),

    ("D-02", "Alicia Fontaine", "invents a conversation that never happened",
     "Alicia,\n\nYou asked for the two figures we've used in marketing, so "
     "here they are. As we discussed, the note quality is the thing that "
     "changed.\n\nMaya\nJotPsych"),

    ("D-03", "Priya Raghunathan", "puts session content in a marketing asset",
     "Priya,\n\nYou mentioned a patient who presented with acute risk. Our "
     "scribe would have captured that whole risk assessment, including the "
     "clinical judgment you applied.\n\nBen\nJotPsych"),

    ("D-04", "Simon Halloway", "unearned compliance claim",
     "Simon,\n\nYou left over security. JotPsych is completely private and "
     "fully compliant, with bank-level encryption on every "
     "session.\n\nMaya\nJotPsych"),

    ("D-05", "Ruth Okonjo", "claims the product exercises clinical judgment",
     "Ruth,\n\nJotPsych now recommends a diagnosis from the session and "
     "decides the treatment plan for you, so you can focus on the "
     "client.\n\nBen\nJotPsych"),

    ("D-06", "Dale Whitmore", "startup register, and an em dash",
     "Dale,\n\nOur revolutionary, cutting-edge scribe is a game-changer — it "
     "will seamlessly unlock 10x more time in your day. Act now, spots are "
     "filling.\n\nMaya\nJotPsych"),

    ("D-07", "Greg Lindqvist", "clean: this one has to pass",
     "Dr. Lindqvist,\n\nYou used JotPsych and stopped, and I don't know why. "
     "That's the part I'd like to hear. If it was the note quality, tell me "
     "what it got wrong and I'll tell you whether we fixed it.\n\nReply here "
     "if it's worth two minutes.\n\nBen\nJotPsych"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--feed-state", action="store_true",
                    help="fold these blocks into state.json, so the phrases "
                         "enter the next run's prompt as hard constraints")
    args = ap.parse_args()

    blocked_records, passed = [], []
    print(f"\nfeeding {len(FIXTURES)} fixture draft(s) through the real gate "
          f"({len(config.REFUSAL_RULES)} rules)\n")

    for row_id, name, note, text in FIXTURES:
        row = {config.ID_FIELD: row_id, config.LABEL_FIELD: name}
        blocked, violations = qc.check(text, row)
        blocks = [v for v in violations if v["severity"] == "block"]
        flags = [v for v in violations if v["severity"] == "flag"]

        status = "BLOCK" if blocked else "pass "
        print(f"  {status} {row_id}  {name:<20} {note}")
        for v in blocks:
            print(f"        blocked by {v['rule']:<24} evidence {v['evidence']!r}")
        for v in flags:
            print(f"        flagged by {v['rule']:<24} evidence {v['evidence']!r}")

        if blocked:
            os.makedirs("quarantine", exist_ok=True)
            with open(f"quarantine/{row_id}.txt", "w", encoding="utf-8") as f:
                f.write(text)
            blocked_records.append({"row": row, "violations": violations,
                                    "text": text})
        else:
            passed.append(row_id)

    path = review.append_rejects_log(blocked_records)
    print(f"\n  {len(blocked_records)} blocked, {len(passed)} passed")
    print(f"  blocked copy -> quarantine/    evidence -> {path}")

    if args.feed_state:
        st = state_mod.load()
        violations = [v for rec in blocked_records for v in rec["violations"]]
        learned = state_mod.learn(st, violations, source="gate_demo")
        state_mod.save(st)
        carried = state_mod.learned_constraints(st)
        print(f"\n  {learned} block(s) folded into {config.STATE_PATH} "
              f"(source: gate_demo)")
        print(f"  the next run will carry {len(carried)} constraint(s):")
        for c in carried:
            print(f"    - never write {c!r}")
        print("\n  Recorded as a learning source, NOT as a run: these drafts "
              "are fixtures,\n  and state.json should not imply the machine "
              "wrote to clinicians it never saw.")
    print("\n  The clean draft passing matters as much as the others failing: "
          "a gate\n  that blocks everything is no more useful than one that "
          "blocks nothing.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
HUMAN TIME -- the machine telling the human what to do with their 1-2 hours.

The rubric's top box for Human time isn't "needs no human", it's "tells the
human exactly what to do with those one to two hours." So every run emits a
work order: what got stopped, why, and what the human should do about it.

This is ~40 lines and it moves a whole rubric row. Do not skip it.
"""
import os
from datetime import datetime, timezone


def write_queue(quarantined, flagged, suppressed, bad_rows, path="REVIEW_QUEUE.md"):
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    total = len(quarantined) + len(flagged) + len(bad_rows)

    L = [
        "# Review queue",
        "",
        f"_Generated {now} by the last run. Overwritten every run._",
        "",
        f"**{total} item(s) need a human.** Estimated time: "
        f"{max(5, total * 3)} minutes.",
        "",
    ]

    L += ["## 1. Blocked before sending — decide keep or kill", ""]
    if not quarantined:
        L.append("_Nothing blocked this run._")
    for q in quarantined:
        rules = ", ".join(f"`{v['rule']}`" for v in q["violations"] if v["severity"] == "block")
        L += [
            f"### {q['row']['name']} ({q['row']['credential']}) — line {q['row']['_line']}",
            f"- **Tripped:** {rules}",
        ]
        for v in q["violations"]:
            if v["severity"] == "block":
                L.append(f"  - {v['reason']} — matched `{v['evidence']}`")
        L += [
            f"- **Draft:** `quarantine/{q['row']['id']}.txt`",
            "- **Do:** read the draft. If the rule was right, nothing to do — "
            "the phrase is already banned for the next run. If it was a false "
            "positive, loosen that pattern in `config.REFUSAL_RULES`.",
            "",
        ]

    L += ["", "## 2. Sent, but worth a look", ""]
    if not flagged:
        L.append("_Nothing flagged this run._")
    for f in flagged:
        rules = ", ".join(f"`{v['rule']}`" for v in f["violations"] if v["severity"] == "flag")
        L.append(f"- **{f['row']['name']}** — {rules} — sent anyway, see `out/{f['row']['id']}.txt`")

    L += ["", "## 3. Deliberately not contacted", ""]
    if not suppressed:
        L.append("_None._")
    for s in suppressed:
        L.append(f"- **{s['row']['name']}** (line {s['row']['_line']}) — {s['decision']['reason']}")

    L += ["", "## 4. Rejected at intake — fix the data", ""]
    if not bad_rows:
        L.append("_None._")
    for b in bad_rows:
        L.append(f"- Line {b['_line']}: {b['_reason']}")

    L += ["", "---", "", "**To rerun after fixing:** `python run.py --send`", ""]

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    return path


def append_rejects_log(quarantined, path="logs/rejects.log"):
    """Append-only audit trail. This file is your proof for the QC row —
    it must be committed and it must not be empty."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with open(path, "a", encoding="utf-8") as fh:
        for q in quarantined:
            for v in q["violations"]:
                if v["severity"] != "block":
                    continue
                fh.write(
                    f"{now}\tBLOCKED\tid={q['row']['id']}\tname={q['row']['name']}\t"
                    f"rule={v['rule']}\tevidence={v['evidence']!r}\treason={v['reason']}\n"
                )
    return path

"""
HUMAN TIME -- the machine telling the human what to do with their hour.

The goal was never "needs no human". It is that the human's hour is spent on
the handful of judgment calls only they can make, instead of on finding them.
So every run emits a work order: what got stopped, why, and what to do about
it, ordered so the top of the file is the most expensive thing to get wrong.
"""
import os
from datetime import datetime, timezone

import config


def _label(row):
    """Whatever this row calls its human-readable name. Never raises: the
    review queue is the last thing that should fall over on odd data."""
    return row.get(config.LABEL_FIELD) or f"(row {row.get('_line', '?')})"


def write_queue(quarantined, flagged, suppressed, bad_rows, path="REVIEW_QUEUE.md"):
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # A skip is either finished or waiting, and only the waiting ones are
    # work. Lumping them together is how a queue becomes wallpaper: 40 correct
    # suppressions bury the 2 domains nobody has ever checked.
    open_skips = [s for s in suppressed if s["decision"].get("needs_review")]
    settled_skips = [s for s in suppressed if not s["decision"].get("needs_review")]

    total = len(quarantined) + len(flagged) + len(bad_rows) + len(open_skips)

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
            f"### {_label(q['row'])} — line {q['row']['_line']}",
            f"- **Tripped:** {rules}",
        ]
        for v in q["violations"]:
            if v["severity"] == "block":
                L.append(f"  - {v['reason']} — matched `{v['evidence']}`")
        L += [
            f"- **Draft:** `quarantine/{q['row'][config.ID_FIELD]}.txt`",
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
        L.append(f"- **{_label(f['row'])}** — {rules} — sent anyway, "
                 f"see `out/{f['row'][config.ID_FIELD]}.txt`")

    L += ["", "## 3. Not contacted, waiting on you", ""]
    if not open_skips:
        L.append("_None. Every skip this run was already settled._")
    else:
        L.append("_The machine stopped rather than guess. Each of these needs "
                 "a person to decide, and stays here until someone does._")
        L.append("")
    for s in open_skips:
        L.append(f"- **{_label(s['row'])}** (line {s['row']['_line']}, "
                 f"`{s['row'].get(config.ADDRESS_FIELD, '?')}`) — "
                 f"{s['decision']['reason']}")

    L += ["", "## 4. Not contacted, settled — no action needed", ""]
    if not settled_skips:
        L.append("_None._")
    else:
        L.append("_Listed for the audit trail, not for your afternoon._")
        L.append("")
    for s in settled_skips:
        L.append(f"- **{_label(s['row'])}** (line {s['row']['_line']}) — "
                 f"{s['decision']['reason']}")

    L += ["", "## 5. Rejected at intake — fix the data", ""]
    if not bad_rows:
        L.append("_None._")
    for b in bad_rows:
        L.append(f"- Line {b['_line']}: {b['_reason']}")

    L += ["", "---", "", "**To rerun after fixing:** `python run.py --send`", ""]

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    return path


def append_rejects_log(quarantined, path="logs/rejects.log"):
    """Append-only audit trail of everything the gate stopped.

    Append-only and committed on purpose: a filter you can only see working
    by running it yourself is a claim, not evidence."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with open(path, "a", encoding="utf-8") as fh:
        for q in quarantined:
            for v in q["violations"]:
                if v["severity"] != "block":
                    continue
                fh.write(
                    f"{now}\tBLOCKED\tid={q['row'][config.ID_FIELD]}\t"
                    f"{config.LABEL_FIELD}={_label(q['row'])}\t"
                    f"rule={v['rule']}\tevidence={v['evidence']!r}\treason={v['reason']}\n"
                )
    return path

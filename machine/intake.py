"""
INTAKE -- reads something the machine did not author.

The rubric is explicit: "a list pasted into the source code is not intake."
So this reads a real file off disk. Swap the file, get different outputs.
"""
import csv
import os


def read_rows(path, required_columns):
    """Return (good_rows, bad_rows). Bad rows carry a reason and never reach
    the LLM -- catching them here is cheaper than catching them downstream."""
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Intake file not found: {path}\n"
            f"This machine reads its input from disk. Put a CSV there and rerun."
        )

    good, bad = [], []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing_cols = [c for c in required_columns if c not in (reader.fieldnames or [])]
        if missing_cols:
            raise ValueError(
                f"{path} is missing required column(s): {', '.join(missing_cols)}\n"
                f"Found: {reader.fieldnames}"
            )

        for i, row in enumerate(reader, start=2):  # start=2 -> header is line 1
            row = {k: (v or "").strip() for k, v in row.items()}
            row["_line"] = i

            empties = [c for c in required_columns if not row.get(c)]
            if empties:
                row["_reason"] = f"missing required field(s): {', '.join(empties)}"
                bad.append(row)
                continue

            if "@" not in row["email"] or "." not in row["email"].split("@")[-1]:
                row["_reason"] = f"malformed email: {row['email']!r}"
                bad.append(row)
                continue

            good.append(row)

    return good, bad

"""
INTAKE -- reads something the machine did not author.

A list pasted into the source is not intake, because nothing outside the
process can change it. This reads a real file off disk: swap the file, get
different outputs, with no deploy.
"""
import csv
import os

import config


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

            # Only validate the address if this machine actually has one to
            # send to. A brief whose outbound isn't email (a Slack post, a
            # row appended to a sheet) just drops ADDRESS_FIELD from
            # REQUIRED_COLUMNS and this check stands down.
            addr_field = config.ADDRESS_FIELD
            if addr_field in required_columns:
                addr = row.get(addr_field, "")
                if "@" not in addr or "." not in addr.split("@")[-1]:
                    row["_reason"] = f"malformed {addr_field}: {addr!r}"
                    bad.append(row)
                    continue

            good.append(row)

    return good, bad

# Review queue

_Generated 2026-08-01T19:25:58+00:00 by the last run. Overwritten every run._

**4 item(s) need a human.** Estimated time: 12 minutes.

## 1. Blocked before sending — decide keep or kill

_Nothing blocked this run._

## 2. Sent, but worth a look

- **Dana Whitfield** — `no_personalization` — sent anyway, see `out/c001.txt`
- **Marcus Oyelaran** — `no_personalization` — sent anyway, see `out/c002.txt`

## 3. Deliberately not contacted

- **Ben Ortiz** (line 7) — suppressed: do_not_contact flag set
- **Sam Delacroix** (line 8) — suppressed: could not classify credential 'Certified Coach' -- we send nothing rather than send generic

## 4. Rejected at intake — fix the data

- Line 9: missing required field(s): name
- Line 10: malformed email: 'rita.nakamura.example.com'

---

**To rerun after fixing:** `python run.py --send`

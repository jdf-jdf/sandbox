# Review queue

_Generated 2026-08-01T06:17:54+00:00 by the last run. Overwritten every run._

**5 item(s) need a human.** Estimated time: 15 minutes.

## 1. Blocked before sending — decide keep or kill

### Priya Raghunathan — line 4
- **Tripped:** `phi_leak`
  - References patient/session content in a marketing asset — matched `a patient who`
- **Draft:** `quarantine/c003.txt`
- **Do:** read the draft. If the rule was right, nothing to do — the phrase is already banned for the next run. If it was a false positive, loosen that pattern in `config.REFUSAL_RULES`.

### Tom Brennan — line 5
- **Tripped:** `fabricated_stat`
  - Numeric claim the machine cannot source — matched `90% reduction`
- **Draft:** `quarantine/c004.txt`
- **Do:** read the draft. If the rule was right, nothing to do — the phrase is already banned for the next run. If it was a false positive, loosen that pattern in `config.REFUSAL_RULES`.

### Alicia Fontaine — line 6
- **Tripped:** `hype`
  - Hype register — reads as tech marketing, not peer-to-peer — matched `revolutionary`
- **Draft:** `quarantine/c005.txt`
- **Do:** read the draft. If the rule was right, nothing to do — the phrase is already banned for the next run. If it was a false positive, loosen that pattern in `config.REFUSAL_RULES`.


## 2. Sent, but worth a look

_Nothing flagged this run._

## 3. Deliberately not contacted

- **Ben Ortiz** (line 7) — suppressed: do_not_contact flag set
- **Sam Delacroix** (line 8) — suppressed: could not classify credential 'Certified Coach' -- we send nothing rather than send generic

## 4. Rejected at intake — fix the data

- Line 9: missing required field(s): name
- Line 10: malformed email: 'rita.nakamura.example.com'

---

**To rerun after fixing:** `python run.py --send`

# Review queue

_Generated 2026-08-01T20:33:04+00:00 by the last run. Overwritten every run._

**4 item(s) need a human.** Estimated time: 12 minutes.

## 1. Blocked before sending — decide keep or kill

_Nothing blocked this run._

## 2. Sent, but worth a look

_Nothing flagged this run._

## 3. Not contacted, waiting on you

_The machine stopped rather than guess. Each of these needs a person to decide, and stays here until someone does._

- **Ingrid Halvorsen** (line 21, `ihalvorsen@umich.edu`) — suppressed pending review: umich.edu came back 'unclear', which is not a verdict this machine acts on. Decide it by hand in data/domain_verdicts.json. (research said: umich.edu is the root domain of the University of Michigan, a public research university, but email-format data shows University of Michigan Medical School personnel also use First.Last@umich.edu / flast@umich.edu addresses while Michigan Medicine's clinical enterprise uses the separate med.umich.edu subdomain — so a @umich.edu address could be a campus student/trainee or a salaried academic medical center employee.)

## 4. Not contacted, settled — no action needed

_Listed for the audit trail, not for your afternoon._

- **Marisol Vega** (line 8) — suppressed: do_not_contact flag set
- **Tobias Grant** (line 18) — suppressed: Tobias Grant <tgrant@cornell.edu> is faculty (Professor of Clinical Psychology, Cornell University), not a trainee, and is employed by the institution rather than buying for themselves. (Simulated record. The sample list is invented, so no real source exists; on a real list tools/classify_people.py writes this field from dated web evidence.)

## 5. Rejected at intake — fix the data

- Line 24: malformed email: 'wfry@'
- Line 25: missing required field(s): name
- Line 26: missing required field(s): mobile

---

**To rerun after fixing:** `python run.py --send`

# Review queue

_Generated 2026-08-01T22:16:41+00:00 by the last run. Overwritten every run._

**7 item(s) need a human.** Estimated time: 21 minutes.

## 1. Blocked before sending — decide keep or kill

_Nothing blocked this run._

## 2. Sent, but worth a look

- **Amara Osei** — `no_personalization` — sent anyway, see `out/C-101.txt`
- **Elena Sokolova** — `no_personalization` — sent anyway, see `out/C-110.txt`
- **Nathan Cole** — `no_personalization` — sent anyway, see `out/C-113.txt`

## 3. Not contacted, waiting on you

_The machine stopped rather than guess. Each of these needs a person to decide, and stays here until someone does._

- **Ingrid Halvorsen** (line 12, `ihalvorsen@umich.edu`) — suppressed pending review: umich.edu came back 'unclear', which is not a verdict this machine acts on. Decide it by hand in data/domain_verdicts.json. (research said: umich.edu is the root domain of the University of Michigan, a public research university, but email-format data shows University of Michigan Medical School personnel also use First.Last@umich.edu / flast@umich.edu addresses while Michigan Medicine's clinical enterprise uses the separate med.umich.edu subdomain — so a @umich.edu address could be a campus student/trainee or a salaried academic medical center employee.)
- **Omar Haddad** (line 13, `ohaddad@ucsf.edu`) — held: reply verdict interested -- a warm reply gets a person, not another campaign email

## 4. Not contacted, settled — no action needed

_Listed for the audit trail, not for your afternoon._

- **Marisol Vega** (line 4) — suppressed: do_not_contact flag set
- **Tobias Grant** (line 11) — suppressed: Tobias Grant <tgrant@cornell.edu> is faculty (Professor of Clinical Psychology, Cornell University), not a trainee, and is employed by the institution rather than buying for themselves. (Simulated record. The sample list is invented, so no real source exists; on a real list tools/classify_people.py writes this field from dated web evidence.)
- **Marcus Feld** (line 16) — suppressed: reply verdict not_interested -- honoring the reply

## 5. Rejected at intake — fix the data

- Line 14: malformed email: 'wfry@'
- Line 15: missing required field(s): name

---

**To rerun after fixing:** `python run.py --send`

# Review queue

_Generated 2026-08-01T19:45:32+00:00 by the last run. Overwritten every run._

**4 item(s) need a human.** Estimated time: 12 minutes.

## 1. Blocked before sending — decide keep or kill

### Simon Halloway — line 32
- **Tripped:** `compliance_overclaim`
  - Vague or unearned security/compliance claim — matched `completely private`
- **Draft:** `quarantine/C-131.txt`
- **Do:** read the draft. If the rule was right, nothing to do — the phrase is already banned for the next run. If it was a false positive, loosen that pattern in `config.REFUSAL_RULES`.


## 2. Sent, but worth a look

_Nothing flagged this run._

## 3. Deliberately not contacted

- **Marisol Vega** (line 8) — suppressed: do_not_contact flag set
- **Nathan Cole** (line 14) — suppressed: kp.org is a known institutional domain, nobody there can buy an EHR add-on
- **Bridget Nolan** (line 15) — suppressed: sutterhealth.org is a known institutional domain, nobody there can buy an EHR add-on
- **Samuel Ortiz** (line 16) — suppressed: providence.org is a known institutional domain, nobody there can buy an EHR add-on
- **Rachel Feinberg** (line 17) — suppressed: med.cornell.edu is a health system or medical organization, so nobody there can buy an EHR add-on. The touch is wasted and the send is noise. (Search shows the cornell.edu medical subdomains belong to Weill Cornell Medicine, a private medical school of Cornell University affiliated with NewYork-Presbyterian/Weill Cornell Medical Center, and med.cornell.edu is its faculty/staff email domain — an academic medical center, not the undergraduate university.)
- **Lucia Moreno** (line 19) — suppressed: mayoclinic.org is a health system or medical organization, so nobody there can buy an EHR add-on. The touch is wasted and the send is noise. (mayoclinic.org is the official web domain of Mayo Clinic, described in sources as a nonprofit American academic medical center for integrated health care, education and research, with campuses in Rochester MN, Jacksonville FL, and Phoenix/Scottsdale AZ and tens of thousands of employed physicians and staff. Anyone at this address is an institutional employee, not an independent buyer.)
- **Devon Pruitt** (line 20) — suppressed: northsidecommunityhealth.org is a health system or medical organization, so nobody there can buy an EHR add-on. The touch is wasted and the send is noise. (The exact domain never appeared in search results, so I could not confirm the specific registrant; however, every organization operating under the name "Northside Community Health Center" that searches surfaced is a nonprofit community health center / FQHC offering primary and behavioral health care, not a university or a private group practice. Clinicians at any of these are institutional employees on an employer-selected system.)
- **Ingrid Halvorsen** (line 21) — suppressed: umich.edu returned verdict 'unclear', which is not in config.DOMAIN_VERDICT_SETTINGS.
- **Omar Haddad** (line 22) — suppressed: ucsf.edu is a health system or medical organization, so nobody there can buy an EHR add-on. The touch is wasted and the send is noise. (UCSF's own materials describe it as a university exclusively focused on health, with graduate-level health professions education, biomedical research, and patient care through its top-ranked hospitals; it has no undergraduate programs, so ucsf.edu is the root domain of an academic medical center rather than a general university campus. Clinicians, faculty, and staff at this address are institutional employees of UCSF/UCSF Health.)
- **Beatriz Salgado** (line 23) — suppressed: peacehealth.org is a health system or medical organization, so nobody there can buy an EHR add-on. The touch is wasted and the send is noise. (peacehealth.org is the corporate domain of PeaceHealth, a nonprofit Catholic health system headquartered in Vancouver, Washington, operating medical centers, critical access hospitals and clinics across Washington, Oregon and Alaska. Clinicians at this address are institutional employees, not independent purchasers.)
- **Caleb Ruiz** (line 34) — suppressed: could not classify credential 'Psychology Doctoral Intern' -- we send nothing rather than send generic

## 4. Rejected at intake — fix the data

- Line 24: malformed email: 'wfry@'
- Line 25: missing required field(s): name
- Line 26: missing required field(s): mobile

---

**To rerun after fixing:** `python run.py --send`

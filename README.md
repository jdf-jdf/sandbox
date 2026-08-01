# Second Timing

A win-back machine for lapsed JotPsych clinicians.

**What it does in one sentence:** reads a list of lapsed clinicians it did not
author (name, email, mobile, nothing else), researches who they actually are,
decides who is worth writing to and what each one should hear, drafts it,
refuses to send anything off-brand, emails what survives with a token that
makes a return traceable, and reports who came back.

Most of these clinicians did not choose against JotPsych. The timing was
wrong: the practice was not ready, the contract had a year left. So the
machine is built for the two things that follow from that. Stay alive with
them until the timing turns, and notice the moment it does.

---

## Change the inputs, get different outputs

```bash
python3 -m venv .venv         # first time only
source .venv/bin/activate     # every new terminal; prompt shows (.venv)
pip install -r requirements.txt
cp .env.example .env          # fill in your keys
python run.py                 # dry run: writes to out/, sends no email
python run.py --send          # live: also emails via Gmail SMTP
```

> On macOS, bare `python` and `pip` don't exist outside a virtualenv, and
> `pip install` without one fails with `externally-managed-environment`. The
> venv fixes both and makes every command below work exactly as written.

**To run it on different data** — one of:

1. Replace `data/lapsed_clinicians.csv` with your file, keep the header row, run again.
2. Or point at it directly, no editing:

```bash
python run.py --input /path/to/your_list.csv --send
```

Required columns: `id, name, email, mobile`. Optional: `do_not_contact`.

That is deliberately the real export and nothing more. The machine is not
handed a credential or a practice type, because JotPsych does not have them:
it goes and finds them (see "Where the machine gets what it wasn't given").
Hand it a richer CSV and any column it carries wins over anything researched.

A second sample is included so the outputs visibly change:

```bash
python run.py --input data/clinicians_sample_b.csv
```

Everything in `out/`, `quarantine/`, `logs/rejects.log`, `REVIEW_QUEUE.md`
and `state.json` will differ on the next run.

**To point it at a different kind of record entirely** — tickets, applicants,
accounts — set `ID_FIELD`, `LABEL_FIELD`, `ADDRESS_FIELD` and `ROUTE_FIELDS`
at the top of `config.py`. Those are the only places anything outside that
file refers to a column by name, and `config.PROMPT` is formatted against the
whole row, so any column is available to it as `{column_name}`. No code
changes.

---

## Where the machine gets what it wasn't given

The export is three columns. Everything the copy depends on (is this a
prescriber or a therapist, do they own the practice, can they buy at all) is
absent from it and present on the open web. So the machine researches its own
inputs, in two passes, both cached, both out of band.

```bash
python tools/classify_domains.py --dry   # what needs researching, calls nothing
python tools/classify_domains.py         # employer, once per domain
python tools/classify_people.py          # the person, only where the domain is unsure
```

**Pass one, per employer.** `@kp.org` is a health system and nobody there can
buy an EHR add-on. `@med.cornell.edu` is an academic medical center and
`@cornell.edu` is a university, and no pattern match gets you that: it is a
fact about the world. Verdicts land in `data/domain_verdicts.json`. This
amortises. Four thousand clinicians at three hundred employers costs three
hundred searches once, and nothing ever again.

**Pass two, per person, and only where pass one was guessing.** A university
verdict is a fact about the campus, not about the clinician standing on it.
The same `cornell.edu` address fits a doctoral student and a professor of
thirty years, and sending the trainee note to the professor is the most
insulting thing this machine could do. So `training` is treated as a
hypothesis and checked by name.

**Titles expire, so verdicts do too.** A 2019 lab page calling someone a
doctoral candidate is evidence about 2019. Every person verdict records the
publication date of the evidence behind it, and anything older than
`PERSON_EVIDENCE_MAX_AGE_MONTHS` (12) stops being trusted and goes back on the
research pile, no matter how confident it was. `--refresh-stale` re-researches
exactly those.

Both passes only ever *write* the cache. `decide.py` only ever *reads* it, so
the decision layer stays deterministic and offline: same CSV plus same cache
gives the same answers, a search outage cannot change who gets contacted, and
a human can open either JSON file and overrule any line in it.

---

## Proving it worked

Every send carries one token, on all three doors a clinician can come back
through:

| door | carries the token as | resolved by |
|---|---|---|
| click | `jotpsych.com/welcome-back/<token>` | web log |
| reply | `you+<token>@gmail.com` | inbox |
| text | nothing (SMS can't) | the mobile number on the row |

The token is an HMAC of the row id and run number, so it is stable, rebuildable
from the CSV if the ledger is lost, and does not leak a customer list when it
shows up in a public URL. Every send is appended to `logs/attribution.jsonl`.

```bash
python tools/returns.py     # the impact report
```

That resolves inbound signals back to named clinicians and reports how many
came back, through which door, how long after, and which segment returns
best. It also counts the ones it *could not* attribute, because that number is
the honest measure of whether the plumbing holds.

The collectors are the sketched part: reading the real web log, inbox and SMS
webhook is three integrations. `data/inbound_sample.jsonl` stands in for all
three in the shape they would emit. Point `--inbound` at a real export and
nothing else changes.

---

## The loop

| Stage | File | What it is |
|---|---|---|
| Intake | `machine/intake.py` | Reads a CSV off disk. Validates. Rejects bad rows before they cost an API call. |
| Decide | `machine/decide.py` | Deterministic segmentation (prescriber vs therapist) and suppression. No LLM. |
| Generate | `machine/generate.py` | Model call with retries and a template fallback so the loop never breaks. |
| **QC gate** | `machine/qc.py` | Refusal rules. Blocks off-brand output *before* it sends. |
| Outbound | `machine/send.py` | Writes a file **and** sends a real email. |
| State | `machine/state.py` | Metrics per run; blocked phrases feed forward into the next run. |
| Human work order | `machine/review.py` | Emits `REVIEW_QUEUE.md`: what the human should spend their time on. |

**Trigger:** `crontab.txt` → `run.sh`. Weekdays at 08:00. Nobody presses anything.

---

## What it refuses to send

The interesting part isn't that there's a filter, it's *what* it filters.
These rules are an opinion about this audience, written as code
(`config.REFUSAL_RULES`):

| Rule | Why |
|---|---|
| `phi_leak` | Any patient or session content in a marketing asset is an existential risk for a HIPAA company. Blocked, no exceptions. |
| `clinical_claim` | Never imply the product exercises clinical judgment. This is the fastest way to lose a licensed clinician. |
| `compliance_overclaim` | "HIPAA-compliant" is precise and legally loaded. "Totally secure" is neither. |
| `replacement_framing` | This audience is defensive about being replaced. Anything that plays there is off-brand. |
| `hype` | Overworked clinicians respond to specificity about their 9pm paperwork, not startup register. |
| `fabricated_stat` | The machine cannot source a number, so it is not allowed to state one. |
| `fake_urgency` | Wrong register for a clinical audience entirely. |
| `unfilled_template` | Mechanical. A `{name}` that reaches an inbox is the worst possible send. |
| `em_dash`, `ai_vocab`, `significance_inflation` | Output that is accurate but reads as machine-written. To a skeptical audience that is its own failure. |

Two soft rules (`too_long`, `no_personalization`) don't block. They send and
flag for a human.

**It also refuses at the decision layer, before generating:** anyone flagged
`do_not_contact`, and anyone whose credential it cannot confidently classify.
An unclassifiable clinician gets nothing rather than something generic.

---

## What it caught

`logs/rejects.log` is append-only and committed. Every line is a draft that
was written and then stopped:

```
BLOCKED  id=c003  rule=phi_leak         evidence='a patient who'
BLOCKED  id=c004  rule=fabricated_stat  evidence='90% reduction'
BLOCKED  id=c005  rule=hype             evidence='revolutionary'
```

The blocked drafts themselves are in `quarantine/`, readable, so you can
judge whether the machine was right.

---

## How it measures and improves itself

`state.json` persists across runs. Each run records what it read, suppressed,
generated, blocked and sent.

The feedback loop: **every phrase that gets a draft blocked is remembered, and
injected into the next run's prompt as an explicit prohibition.** Run the
machine twice and the second run starts with:

```
carrying 3 learned constraint(s) from previous runs:
  - never write 'a patient who'
  - never write '90% reduction'
  - never write 'revolutionary'
```

The rejection rate per run is printed at the end of every run and stored in
`state.json`.

> **Caveat, stated plainly:** the learning loop acts on the *prompt*, so it
> only moves the rejection rate on the model path. With no `ANTHROPIC_API_KEY`
> set, the generator falls back to a fixed template, which by definition
> cannot learn, and the rate stays flat. Set the key to see the loop close.

---

## Human time

The budget is one to two hours a month, and the machine says what to spend it
on. Every run rewrites `REVIEW_QUEUE.md` with four sections:

1. **Blocked, decide keep or kill.** Each with the rule it tripped, the exact
   matched text, a path to the draft, and what to do about it.
2. **Sent, but worth a look.** Soft flags.
3. **Deliberately not contacted**, and why.
4. **Rejected at intake, fix the data**, with line numbers.

---

## What is stubbed

- **Outbound recipient** is `SEND_TO` (a single inbox), not each clinician's
  real address. One environment variable away from real.
- **Intake** is a CSV on disk rather than a live CRM or sheet. The reader is
  isolated in `machine/intake.py`; swapping the source is one function.
- **`machine/send.py:GmailAPISender`** is a placeholder. SMTP is the live path.

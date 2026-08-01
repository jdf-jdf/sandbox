# [MACHINE NAME] — a machine for [WHAT IT DOES]

> **Tomorrow: rewrite the bracketed parts and delete this line.** Everything
> else in this file is already true of the code and can stay as-is.

**What it does in one sentence:** reads a list of behavioral-health clinicians
it did not author, decides who to contact and what each one should hear,
drafts it, refuses to send anything off-brand, and emails what survives.

---

## Change the inputs, get different outputs

This is the part that makes it a machine rather than a picture of one.

```bash
pip install -r requirements.txt
cp .env.example .env          # fill in your keys
python run.py                 # dry run: writes to out/, sends no email
python run.py --send          # live: also emails via Gmail SMTP
```

**To run it on your data instead of ours** — one of:

1. Replace `data/clinicians.csv` with your file, keep the header row, run again.
2. Or point at it directly, no editing:

```bash
python run.py --input /path/to/your_list.csv --send
```

Required columns: `id, name, credential, practice_type, email`.
Optional: `do_not_contact`, `notes`.

A second sample is included so you can watch the outputs change immediately:

```bash
python run.py --input data/clinicians_sample_b.csv
```

Everything in `out/`, `quarantine/`, `logs/rejects.log`, `REVIEW_QUEUE.md`
and `state.json` will differ on the next run.

---

## The loop

| Stage | File | What it is |
|---|---|---|
| Intake | `machine/intake.py` | Reads a CSV off disk. Validates. Rejects bad rows before they cost an API call. |
| Decide | `machine/decide.py` | Deterministic segmentation (prescriber vs therapist) and suppression. No LLM. |
| Generate | `machine/generate.py` | LLM call with retries and a template fallback so the loop never breaks. |
| **QC gate** | `machine/qc.py` | Refusal rules. Blocks off-brand output *before* it sends. |
| Outbound | `machine/send.py` | Writes a file **and** sends a real email. |
| State | `machine/state.py` | Metrics per run; blocked phrases feed forward into the next run. |
| Human work order | `machine/review.py` | Emits `REVIEW_QUEUE.md` — what the human should spend their time on. |

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

Two soft rules (`too_long`, `no_personalization`) don't block — they send and
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

The blocked drafts themselves are in `quarantine/` — readable, so you can
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

> **Honest caveat:** the learning loop acts on the *prompt*, so it only shows a
> falling rejection rate on the LLM path. With no `ANTHROPIC_API_KEY` set the
> generator falls back to a fixed template, which by definition cannot learn —
> the rate stays flat. Set the key to see the loop close.

---

## Human time

Budget is 1–2 hours a month, and the machine tells you what to do with it.
Every run rewrites `REVIEW_QUEUE.md` with four sections:

1. **Blocked — decide keep or kill.** Each with the rule it tripped, the exact
   matched text, a path to the draft, and what to do about it.
2. **Sent, but worth a look.** Soft flags.
3. **Deliberately not contacted**, and why.
4. **Rejected at intake — fix the data**, with line numbers.

---

## What is stubbed

Stated plainly, per the brief's instruction to mark sketched parts:

- **Outbound recipient** is `SEND_TO` (your own inbox), not the clinician's
  real address. One env var away from real.
- **Intake** is a CSV on disk rather than a live CRM or sheet. The reader is
  isolated in `machine/intake.py`; swapping the source is one function.
- **`machine/send.py:GmailAPISender`** is a placeholder. SMTP is the live path.

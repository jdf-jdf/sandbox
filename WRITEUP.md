# Second Timing

A win-back machine for the ~15,000 clinicians who tried JotPsych and stopped.

## The recommendation

**Do not build a re-engagement campaign. Build a machine that earns the right
to write, and that can prove a return.**

The brief's own diagnosis is the whole design: these clinicians mostly did not
choose against JotPsych, the timing was wrong. That has two consequences and
they point in opposite directions from a normal campaign.

First, if timing is the problem, volume is not the answer. Writing to all
15,000 is how you burn the list before the timing turns. So the machine's most
important output is the sends it *refuses to make*: it declines to write to
anyone it cannot say something true and specific to, and it says why, on the
record, every time.

Second, "notice the moment it does" is not reporting, it is plumbing. It has
to be solved at the moment of sending or it cannot be solved at all. Every
send therefore carries a token before it leaves the building.

The uncomfortable part is the input. The export is three columns: name, email,
mobile. Nothing in it tells you whether someone is a prescriber or a
therapist, owns a practice, or can buy at all, and a win-back email that does
not know which of those is true is a mail merge. So the machine's first real
act is to go and find out. It researches the employer once per domain, then
the individual person where the employer's answer is not enough, caches both,
and only then decides. Reading the open web well is not decoration here. It is
what makes three columns into a segmented list.

## The four layers

| Layer | This machine |
|---|---|
| Intake it did not author | `data/lapsed_clinicians.csv` — the real export shape: id, name, email, mobile |
| Decision it makes alone | Two-axis routing (segment × setting), two researched caches, six suppression paths, no LLM |
| Action that leaves the process | A multipart email in a real inbox, tokenised for attribution |
| Trigger that is not a person | `crontab.txt` → `run.sh`, weekdays 08:00 |

The layer kept deliberately thin is generation. It gets one short prompt, low
reasoning effort, and no authority: it cannot decide who to write to, cannot
choose a segment, and cannot place the tracking link. Everything a model could
get wrong that a rule could get right is a rule.

## The numbers it reports

Run `./evidence.sh --send` for a clean three-run sequence.

| | |
|---|---|
| read → sent, per run | 33 → 18 |
| suppressed, with a stated reason | 12 |
| rejected at intake (bad data) | 3 |
| refusal rules in the gate | 19 |
| blocked by the gate across three live runs | **0** |
| clinicians who came back | 5 of 24 written to (20.8%) |
| returns the machine could not attribute | 1 |
| median days to return | 6 |

**That zero is the honest number and it needs saying.** Across three live
runs of 18 sends, the gate blocked nothing, and even `data/gate_test.csv` (six
rows built to bait statistics, hype, PHI and invented rapport) came back clean.
The reason is that `config.PROMPT` forbids those failures up front, so the
model largely does not commit them. That is the right outcome for the product
and a bad one for evidence: a gate that never fires is indistinguishable from
no gate. So `python tools/gate_demo.py` feeds the real gate seven fixture
drafts (each one a draft this machine actually wrote earlier in the build, or a
close paraphrase) and shows what it catches:

```
BLOCK D-01  fabricated_stat '90% reduction' + unsourced_quantity '30 hours a month'
BLOCK D-02  fabricated_relationship 'You asked for'
BLOCK D-03  phi_leak 'a patient who' + clinical_claim 'clinical judgment'
BLOCK D-04  compliance_overclaim 'completely private'
BLOCK D-05  clinical_claim 'recommends a diagnosis'
BLOCK D-06  hype 'revolutionary' + fake_urgency 'Act now' + em_dash '—'
pass  D-07  clean draft, correctly untouched
```

Six blocked on ten rule hits, one clean draft through. The drafts are
fixtures; the gate is the real one, and the blocks land in `logs/rejects.log`
and `quarantine/` in the same format a live run writes.

The return numbers come from `python tools/returns.py`. They are the only outcome
numbers here; everything else is process. A machine that reports a falling
rejection rate and cannot tell you whether anyone came back is measuring its
own throat-clearing.

The unattributable return is in that table on purpose. It is the honest
measure of whether the plumbing holds, and it will never be zero.

## What it refuses to send

The gate is an opinion about this audience written as code, not a spam filter.
Three of the nineteen rules matter more than the rest:

- **`phi_leak`** — a marketing asset that references patient or session
  content is an existential problem for a HIPAA company, not an embarrassment.
- **`clinical_claim`** — implying the product exercises clinical judgment
  loses this audience permanently and invites a regulatory question.
- **`fabricated_relationship`** — the model, given a win-back list, will
  cheerfully invent a conversation that never happened ("you asked for the two
  figures we quote"). Having once been a customer is real shared history; the
  model inflates it. This rule was added after reading actual drafts.

**The rule I expect to be argued with is `em_dash`, and I kept it.** It blocks
copy that is otherwise correct, purely for a punctuation mark. The argument
against is that it is cosmetic. The argument for is that this audience is
being pitched AI tools daily and has learned the tells, so an em dash is not a
style question, it is a credibility question. It earns its keep in
`tools/gate_demo.py` (D-06), and it is the rule most likely to be quietly
deleted by someone who has not sat in front of this audience.

`logs/rejects.log` is what the gate stopped and `quarantine/` holds the blocked
copy, so a reader can judge whether it was right rather than take my word for
it. Two fixtures exist, and they do different jobs:

```bash
python run.py --input data/gate_test.csv   # bait the MODEL (it resists: 0 blocked)
python tools/gate_demo.py                  # test the GATE directly (6 of 7 blocked)
```

The first failing to produce a block is a result, not a gap. It says the
constraints in the prompt are doing the work upstream of the gate, which is
where you want the work done.

## Where the one to two hours a month go

`REVIEW_QUEUE.md` is ordered so the hour is spent on judgment, never on
triage. Suppressions that are **finished** ("researched, and Mayo Clinic
employees cannot buy") never appear. Only suppressions that are **waiting on a
person** do, flagged `needs_review`.

That distinction is what makes the budget hold at scale. Domain research
amortises: 4,000 clinicians at 300 employers is 300 searches once and zero
thereafter. Person research does not amortise, so it runs only where the
domain verdict was a guess, which is a small slice of a large list. Everything
else is a cache read.

The human's hour goes to three things: overruling a researched verdict they
know is wrong (both caches are plain JSON, and the run trusts the file over
the model), deciding the `unclear` domains, and reading the flagged-but-sent
copy.

## What week two looks like

Week one ships the loop above. Week two is the part that turns a send into a
relationship:

1. **Wire the collectors.** The tokens and the resolution are real; the web
   log, inbox and SMS webhook that feed them are simulated by
   `data/inbound_sample.jsonl`. This is a day of integration and it converts
   every number in the impact table from demonstrated to live.
2. **Cadence and a real second touch.** Today three runs write to the same 18
   people. The machine needs to know when it last wrote to someone and what it
   said, so that "stay alive until the timing turns" means a sequence over
   months rather than a repeat.
3. **Use the mobile column.** It is one of the three things the export gives
   us and today it only serves as an attribution fallback. For a low-frequency,
   high-signal touch to a clinician who has ignored two emails, SMS is the
   right channel and the consent question is answerable.
4. **Feed returns back into targeting.** The impact report already knows which
   segment returns best. Nothing yet uses that to decide who gets written to
   next.

## What is real, what is sketched

**Real:** intake, both research passes and their caches, routing, suppression,
generation with retry and template fallback, the 19-rule gate, quarantine,
multipart email over live SMTP, the attribution tokens and ledger, the returns
resolution, the review queue, the metrics, the learning loop, cron.

**Sketched, and marked:** the inbound collectors (simulated by
`data/inbound_sample.jsonl`); `data/person_verdicts.json` for the sample,
because the sample clinicians are invented and therefore unresearchable — on a
real list `tools/classify_people.py` writes it from dated web evidence, and
every simulated record says `"source": "simulated"`; and SMS as a sending
channel.

**What breaks first if this ran unattended for a month:** the person cache
going stale. Titles expire, and the 12-month recency bar means verdicts age
out into the review queue rather than silently staying true. That is the
correct behaviour, but it means the queue grows quietly over time, and the
first symptom is a rising `needs_review` count rather than anything visibly
broken. `python tools/classify_people.py --refresh-stale` is the fix, and it
should be on the same cron as the run.

## How AI was used

Claude Code wrote most of this repository, under close review. Three things
are worth separating out.

The **research on JotPsych** (the $5M Base10 seed, the 2026 JotAudit and JotRx
launches, the shift from scribe toward agentic EHR, and the NPR coverage on
therapist AI note-taking and consent) was done with web search and shaped both
`SEGMENT_BRIEF` and the refusal rules. That reading is why the prescriber brief
talks about audit exposure and reimbursement rather than generic time savings.

The **`unsourced_quantity` rule came out of that research.** JotPsych's own
press release claims a 90%+ documentation-time reduction; the "30 hours per
month" figure that circulates alongside it appears in no company source I could
find. `fabricated_stat` only caught percentages, so a rule was added for
time-saved claims that carry no percent sign.

The **`fabricated_relationship` rule came from reading the machine's own
output**, not from planning. An early draft opened "You asked for the two
figures we've used in marketing," which was a relationship the machine had
invented. That is the loop this repository is arguing for: run it, read what
came out, and write the rule.

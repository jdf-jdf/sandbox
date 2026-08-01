Joanna Flores — Second Timing — 2026-08-01

# Second Timing

**Do not build a re-engagement campaign. Build a machine that earns the right
to write, and that can prove a return.**

These clinicians mostly did not choose against JotPsych: the timing was
wrong. That cuts two ways. Writing to all 15,000 burns the list before the
timing turns, so the machine's most important output is the sends it
*refuses to make*, each with a reason on the record. And "notice the moment
it comes back" is plumbing, not reporting: it has to be solved at the moment
of sending, so every send carries an attribution token before it leaves the
building.

The export is three columns — name, email, mobile — and nothing in it says
who can buy. So the machine's first act is research: the employer once per
domain, the person only where that answer is not enough, both cached. Intake
it did not author → two-axis routing (segment × setting), deterministic, no
LLM → a 23-rule quality gate → a real email, tokenised → `crontab.txt`,
weekdays 08:00, plus a monthly check that the brand voice itself hasn't gone
stale. Full architecture, every refusal rule, and the dead ends that got us
here are in `README.md`.

## The numbers

Run `./evidence.sh --send` for a clean sequence: run 1 live, runs 2–3 dry.
These are from one such sequence, on a 15-row sample (`data/lapsed_clinicians.csv`).

| | |
|---|---|
| read → sent, per run | 15 → 10 |
| suppressed, with a stated reason | 3 |
| rejected at intake (bad data) | 2 |
| refusal rules in the gate | 23 (17 block, 6 flag) |
| blocked by the gate on that pass | **0** |
| clinicians who came back | 3 of 10 written to (30%) |
| returns the machine could not attribute | 1 |
| median days to return | 3 (range 2–18) |

**That low block count is the honest number.** The prompt forbids the
failures up front, so the model mostly doesn't commit them — right for the
product, bad for evidence. So `python tools/gate_demo.py` feeds the real gate
seven fixture drafts (each one this machine actually wrote earlier in the
build):

```
BLOCK D-01  fabricated_stat '90% reduction'
BLOCK D-02  fabricated_relationship 'You asked for'
BLOCK D-03  phi_leak 'a patient who' + clinical_claim 'clinical judgment'
BLOCK D-06  hype 'revolutionary' + fake_urgency 'Act now' + em_dash '—'
pass  D-07  clean draft, correctly untouched
```

Six of seven blocked; the checks are the real ones, and the blocks land in
`logs/rejects.log` and `quarantine/` in the same shape a live run writes.

The three returns span all three attribution doors — a click (`Marcus Feld`,
+2 days), a reply (`Nathan Cole`, +3 days, "I'm leaving the health system in
January"), and a text (`Aisha Mbeki`, +18 days) — resolved from
`logs/attribution.jsonl` against `data/inbound_sample.jsonl`, which stands in
for the real web log, inbox and SMS webhook. Nathan Cole's reply is the case
for the next section: he was in the `institutional` segment.

## The one call worth arguing about

`SUPPRESS_INSTITUTIONAL = False`. Clinicians at a health system address get
written to, in the `institutional` register — not pitched a purchase they
can't authorise. The case for suppressing them (they can't buy, it's waste)
is real; the case against is that "can't buy today" is exactly the premise
this brief rejects, and a salaried clinician is one job move from private
practice. This run's own evidence makes the case: Nathan Cole, `kp.org`,
replied "I'm leaving the health system in January." Flip the flag in
`config.py` and rerun to see the other answer.

## Where the one to two human hours a month go

**Not on reviewing what it wrote.** Keeping that cheap is the point of the
queue, not the use of the hour. `REVIEW_QUEUE.md` is rewritten every run and
ordered so finished suppressions never appear; only ones **waiting on a
person** do — 1 of 15 on this sample. Domain research amortises (300 employers
is 300 searches, once); person research runs only where the domain verdict was
a guess. Clearing that queue is ten minutes.

The rest of the hour goes to the three things the machine cannot do for
itself.

**Tell it where the warm funnel is.** The machine can research a domain and
rank a list. It cannot know that we just put an SDR in Portland, that a
partner introduced us to a twelve-clinician group, or that someone opened four
emails last quarter and never replied. That intelligence sits in the CRM and
in people's heads, and it is worth more than anything the open web will tell
us. Getting it in is a column on the intake CSV and a line in `config.py` —
which is the whole reason the input is a file the machine did not author.

**Argue about positioning with GTM, out loud.** What the machine says is
downstream of what we have decided we are. `BRAND_BRIEF`, `APPROVED_CLAIMS`
and `SEGMENT_BRIEF` are human-authored files: they are where a conversation
about story and register turns into something executed identically across
4,000 clinicians. An hour of that beats an hour of proofreading, because it
changes every future send rather than one.

**Run it, and read what came back.** The loop only improves if a person reads
the output and writes the rule. `fabricated_relationship` exists because
someone read a draft that had invented a conversation. No amount of planning
produced that rule; reading a dozen drafts did.

Once a month, ten of those minutes go to `BRAND_REVIEW.md` — the site-diff
`tools/brand_check.py` writes, so the prompt never quietly drifts back to
describing a product JotPsych stopped selling.

## What week two looks like

1. **Wire the collectors.** Tokens and resolution are real; the web log,
   inbox and SMS webhook feeding them are simulated by
   `data/inbound_sample.jsonl`. A day of integration turns every number above
   from demonstrated to live.
2. **Cadence, and a real second touch** — know when someone was last written
   to and what was said, so three runs stop meaning "the same 10 people
   three times."
3. **Use the mobile column** to send, not just to attribute a text back.
4. **Feed returns into targeting.** The report already knows which segment
   returns best; nothing yet acts on it.

Full detail on architecture, every refusal rule and why, the dead ends that
shaped the design, and how AI was used, is in `README.md`.

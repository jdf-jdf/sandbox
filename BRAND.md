# JotPsych, as the brand actually stands

Everything the machine believes about JotPsych comes from here. `config.py`
quotes this file; this file explains the quotes and says where each fact came
from. When the brand moves, this is the thing a human edits, and the config
constants get dragged along behind it.

Read from the public site on **2026-08-01**. Every claim below is sourced. If
a line has no source, it does not belong in this file.

---

## There is no one sentence

The homepage does not have a headline. It has three, served at random from the
same URL. Read it three times and you get three different companies:

> "The behavioral health **AI scribe** that defends you from insurance
> companies. It writes your note from the visit, built to survive the audit and
> beat the downcode."

> "The behavioral health **EHR** that defends you from insurance companies.
> Notes, billing, and your whole practice in one system that scans every note
> and claim against 150+ payer rules, works the denials, and follows every
> dollar from the visit to your bank account. One step ahead of the payers."

> "**Your whole behavioral health practice. One system.** Notes,
> e-prescribing, scheduling, telehealth, billing, and credentialing on one
> platform, for every clinician you employ. The whole practice, one login."

— all three from [jotpsych.com](https://jotpsych.com), observed across
consecutive reads on 2026-08-01.

This is worth more than any single one of them, because it says what the
company is still arguing with itself about: whether it leads with the scribe,
the EHR, or the consolidation. Do not copy a hero line into our voice. It is
the least stable sentence on the site.

What holds across all three, and is therefore what we can actually rely on:

- **Behavioral health, specifically.** Never general healthcare.
- **The practice, not the note.** Even the scribe variant sells the note as a
  defensive instrument rather than as time saved.
- **Payers are the opponent** in two of the three, and nowhere is the promise
  a better work-life balance.

`tools/brand_check.py` samples each page several times per run for exactly
this reason, and remembers every variant it has seen. The first version of
that tool fetched once, and duly reported the homepage as rewritten three runs
running.

## What changed, and why it is the whole campaign

JotPsych launched in 2023 as an ambient scribe. The stated goal then was to
"eliminate administrative overhead for behavioral health clinicians"
([seed announcement](https://www.jotpsych.com/post/jotpsych-raises-seed-round)).
It is now a full EHR with billing attached, funded by a $5M seed led by Base10.
The company's own framing of what it is replacing: most EHRs are "passive
repositories," and what they are building is "the spinal cord of behavioral
health" (same source).

This matters more to this machine than to any other piece of JotPsych
marketing, because **our list left the scribe.** They tried a note-taker,
stopped, and have never seen the billing side. That is not a pitch, it is news,
and it is the only honest reason we have to write to someone who already
churned once.

It is also the trap. News is only news to someone who could act on it. A
clinician employed by a hospital cannot buy an EHR, and a resident cannot buy
anything at all. Telling them what changed is a pitch wearing a hat. So the
news is gated by setting: see `BRAND_NEWS_BY_SETTING` in `config.py`.

## The antagonist

The brand has one, which is unusual for health software and is the sharpest
thing about it: **payers**. Not burnout, not admin in the abstract. Insurance
companies, denials, and the gap between the care given and the dollar
collected.

The register that follows from that is adversarial-on-your-behalf, not
aspirational. "Defends you." "Works the denials." "One step ahead." Nothing in
JotPsych's own copy promises the clinician a better life; it promises them a
better position against a specific opponent.

Two things follow for our emails. Documentation is a means, not the subject.
And the payer frame is real leverage with prescribers, whose brief in
`SEGMENT_BRIEF` already worries about coding and clawback, which is the same
fear from the other end.

## What we sell

The pillars, in the brand's own words
([/for-clinicians](https://jotpsych.com/for-clinicians)):

> "Start your practice. / Write the chart while you work. / Get paid for what
> you do."

The named modules. **This list is exhaustive.** Anything shaped like a JotPsych
product name and not on it does not exist, which is why `qc.py` blocks unknown
`Jot*` names outright:

| Module | What it does |
|---|---|
| AI Scribe | Drafts the note during the session. Psych-trained. History, problem lists, medications, assessments. |
| JotBill | Claims, denials, appeals, patient statements. |
| JotCred | Panel enrollment with commercial payers and Medicare, plus a credentialing tracker. |
| JotAudit | Flags weak documentation *before* you sign it. |
| JotSite | Brand-matched practice website, live in 10 business days. |
| JotRx | E-prescribing, including EPCS for controlled substances. |
| JotMeet | Telehealth. |

The consolidation argument, aimed at anyone paying for more than one thing:

> "Stop paying seven vendors." / "Your stack is bleeding you dry." / "Built for
> a practice of 1. And the one you're becoming."
> — [/for-clinicians](https://jotpsych.com/for-clinicians)

## Money, in public

Published, so quotable ([/pricing](https://jotpsych.com/pricing)):

- Moonlighting **$53/mo** ($637/yr), "for occasional clinical work"
- Basic **$135/mo** ($1,620/yr), "for full-time clinicians and practices",
  marked most popular
- Everything **$269/mo** ($3,229/yr)
- Custom, for 7+ seats
- "No long-term contracts required • Upgrade anytime"
- "No credit card required to start"

Add-ons are priced separately (JotBill runs 4–8% of collections, JotAudit
$62/mo, JotSite $99 setup plus $49/mo). The solo brief in `config.py` says
outright that these clinicians will ask about price. Now the machine can answer
instead of deflecting.

## The published numbers

These are real and attributable, which is exactly why they are dangerous: they
are also the most vendor-sounding sentences available to us. They live in
`APPROVED_CLAIMS` and the QC gate will pass them **only word for word**. Any
paraphrase trips `fabricated_stat` or `unsourced_quantity` and the draft is
quarantined.

| Claim | Source |
|---|---|
| 90% less documentation time | [seed announcement](https://www.jotpsych.com/post/jotpsych-raises-seed-round) |
| Average 30 hours a month saved | [jotpsych.ai](https://www.jotpsych.ai/) |
| 10,000+ practices | [jotpsych.com](https://jotpsych.com) |
| 2.5M+ notes written | [jotpsych.com](https://jotpsych.com) |
| 45M+ audit-rule checks | [jotpsych.com](https://jotpsych.com) |
| 150+ payer rules | [jotpsych.com](https://jotpsych.com) |

A note on judgment, since the gate cannot supply it: "the average clinician
saves 30 hours a month" is true, sourced, and still the single most ignorable
sentence you can put in front of someone who has already tried the product and
left. `humanizer-context.md` says it plainly: saves-you-time is what every
vendor says. The allowlist exists so the machine *can* reach for a number, not
so it should.

## How it sounds

Short declaratives. Second person. The verb does the work ("defends", "scans",
"works the denials", "follows every dollar"). No hedging, no adjective stacks,
and no promises about transformation.

Testimonials on the site are clipped to a line and attributed by initials and
credential, which is the register clinicians trust:

> "Better quality note, better interface, better service." — NS, Solo
> Psychiatrist
>
> "I went from one intake a day to four, without sacrificing quality." — AM,
> Psychiatric NP

We do not reuse these. They are here as evidence of the voice, and quoting a
customer at a churned customer is its own kind of insult.

## Words

**clinicians**, never "providers". The site uses "clinicians" throughout,
including the heading "What *clinicians* are saying".

**clients**, on the site, for the people they see. Our own rule is narrower and
stays as it is: prescribers say patients, therapists usually say clients. See
`humanizer-context.md`. The site is writing to a room; we are writing to one
person whose credential we looked up.

**the chart**, **the note**, **the claim**. Concrete nouns. Never "the
platform", never "the solution", never "documentation burden" (say notes, or
paperwork, or charting).

**the downcode**, **survive the audit**, **work the denial**. The brand's own
vocabulary for the fight, taken from the hero variants above. Worth using with
prescribers, whose fear of an undercoded note is the same fear from the other
end. Worth avoiding with therapists, who mostly do not live in that world.

Words the brand does not use and the gate now blocks: transform your practice,
revolutionize, frictionless, one-stop shop, all-in-one solution. Note that
"one-stop shop" appears on the site *inside a customer quote* and never in
JotPsych's own voice, which is the distinction the rule encodes.

## What this file does not license

Being an EHR now does not make the machine's job a demo. The recipient tried
this product and stopped, we do not know why, and the brief that governs every
draft still says asking beats guessing. Brand knowledge earns us one accurate
sentence about what the product is. It does not earn us a paragraph.

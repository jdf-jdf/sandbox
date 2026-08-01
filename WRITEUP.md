# [MACHINE NAME]

> Fill every bracket in, or delete this file. A half-filled template is worse
> than no writeup.

## What it does

[One paragraph. What goes in, what comes out, who it is for. No architecture
yet.]

## The four layers

| Layer | This machine |
|---|---|
| Intake it did not author | [___] |
| Decision it makes alone | [___] |
| Action that leaves the process | [___] |
| Trigger that is not a person | [___] |

[One paragraph on the thing you deliberately kept thin, and why. Where the
seams are is more interesting than where the polish is.]

## What it refuses to send, and why

[The refusal rules are an opinion, not a spam filter. Say what the opinion is:
what would be off-brand for this audience, and what is merely bad writing.
Point at `logs/rejects.log` for what it actually caught, and at `quarantine/`
so a reader can judge whether it was right.]

[Name at least one rule you expect to be argued with, and say why you kept it.]

## What the human does

[The budget is one to two hours a month. Say what lands in `REVIEW_QUEUE.md`,
in what order, and why that order. The claim is not "no human needed"; it is
"the human's hour goes to the judgment calls only they can make".]

## How it measures itself

[The rejection rate across runs, from `state.json`. State the number honestly,
including if it did not move. A flat line you can explain is worth more than a
falling line you cannot.]

## The read on this audience

[What you believe about these people that a generic version of this machine
would get wrong. This should already be visible in `config.SEGMENT_BRIEF` and
`config.REFUSAL_RULES`; here is where you say it in words.]

## What is stubbed, and what breaks first

[List them plainly. Then: if this ran unattended for a month, what is the
first thing that would go wrong, and how would you know?]

## Provenance

[If you started from an existing scaffold of your own, say so here and say
what was already there versus what you built for this brief. Reusing your own
tooling is normal engineering practice; letting a reader discover it
themselves is what turns it into a problem.]

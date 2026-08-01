# Second Timing

A win-back machine for clinicians who tried JotPsych and stopped.

## The short version

More than 15,000 clinicians have tried JotPsych. Thousands of them are not
paying today, and most of them never looked at the product and decided against
it. The timing was wrong. The practice was not ready, the old contract had a
year to run, the group had not felt the pain yet.

That one fact decides everything else on this page. If timing is the problem,
then sending more email is not the answer, because you only get to burn a list
once. The job is to stay worth hearing from until the timing turns, and to
notice the moment it does.

So this machine reads a list of lapsed clinicians, works out who each person
actually is, decides which of them it can say something true and specific to,
writes to those and only those, refuses to send anything that would embarrass
us, and can tell you afterwards who came back and how.

It runs on a schedule. Nobody presses anything.

## What we were handed, and why that is the hard part

The export is three columns: a name, an email address, and a mobile number.
That is all a signup ever gave us.

A second sample is included so the outputs visibly change. Same three columns,
different people:

So the machine's first real act is to go and find out. It researches the
employer behind each email address, then researches the individual person where
the employer's answer is not enough on its own. Both answers get saved, so the
same question is never paid for twice.

That one reads 8 and sends 6. The two it declines show both halves of the
decision layer: `felix@aurandcounseling.com` is a do-not-contact flag, which is
finished, and `sbhatt@cornell.edu` is a person the domain pass could only call
`trainee`, which is work. Everything in `out/`, `quarantine/`,
`logs/rejects.log`, `REVIEW_QUEUE.md` and `state.json` differs on the next run.

## The marketing call we made

**We did not build a re-engagement campaign. We built something that earns the
right to write, one person at a time, and can prove it when someone comes
back.**

Everything below follows from that.

**Restraint is the product.** The most important thing this machine does is
decline to send. If it cannot say something true and specific to a person, it
writes nothing and records why. A campaign optimises for how many go out. This
optimises for not spending someone's goodwill on a message that was not worth
their attention.

**This is a win-back, not an introduction.** They have used the product. They
know what it is. Explaining it back to them reads as though nobody checked the
file. What we genuinely do not know is why they left, and inventing a reason is
worse than asking for one.

**We ask for a call, not a reply.** Why someone stopped is almost always more
complicated than what they would type into an email. A specific, small ask is
easier to answer than a blank one.

**We say plainly when we know someone cannot buy.** A clinician employed by a
hospital did not choose their documentation system and cannot switch it. So we
do not pitch them. We say we know they may not get to choose, ask whether they
are staying put, and ask who at their organisation actually evaluates these
tools. Being the vendor who understood their situation is the whole play, and
it costs nothing to be that vendor a year early. This is not a hypothesis. One
of the five clinicians who came back on the last run was employed by a health
system, and he replied to say he is leaving it in January.

**We read the market before writing a word.** JotPsych's own positioning (the
seed round, the 2026 JotAudit and JotRx launches, the move from note-taker
toward something that acts inside the record) is why the prescriber copy talks
about coding and audit exposure rather than generic time savings. Public
reporting on how therapists and their clients feel about AI in the room is why
the therapist copy is quieter and more careful about consent. That reading is
in the machine, not in a slide.

## Who we are actually writing to

Two questions, answered separately, because they do different jobs.

**What do they do?** This decides what the email is about.

| | Their working day | What they actually care about |
|---|---|---|
| **Prescribers** (MD, DO, PMHNP, NP) | Short, high-volume medication visits | Getting paid correctly. An undercoded note loses money quietly, and an overcoded one invites a clawback. They do their own maths, so be specific or say nothing. |
| **Therapists** (PhD, PsyD, LCSW, LMFT, LPC) | Fifty-minute sessions, narrative notes | The paperwork that follows them home, and the fear that a tool will flatten the nuance they are paid for. More protective of privacy, more sceptical of AI. |
| **Not established** | Unknown | We write about the part both share, documentation that follows you home, and let the rest come from where they work. We do not guess. |

**Where do they work?** This decides whether we write at all, and in what
register.

| | Who they are | What we say |
|---|---|---|
| **Solo** | Reached at a personal address. They are the practice: no admin, no billing staff, nobody to ask | The easiest sale and the least forgiving audience. Price comes up and they will ask. Never write as if they have a team. |
| **Practice owner** | Reached at a domain they appear to own | They buy for other people too, so they think about onboarding, about adoption, and about what happens to the notes if a clinician leaves. |
| **Employed by an institution** | Hospital, health system, academic medical centre | They cannot buy, and a discount is meaningless to them. Write anyway, because clinicians leave for private practice constantly. Be worth answering rather than persuasive. |
| **Still in training** | A university address that is not a medical centre | They cannot buy today and they pick their own tools the moment they finish. Check the premise rather than assume it, ask one honest question, do not pitch. |

Someone holding two credentials is common here, and the prescribing one wins,
because a person who can write a prescription has the prescriber's problem.
That is a deliberate choice, not an accident of which rule happened to come
first.

## How you write to a clinician without losing them

These people are pitched an AI tool most weeks and have learned the tells. The
rules below are not style preferences. Each one is a way we could lose someone
permanently.

**Never sound like the software makes clinical decisions.** This is
disqualifying rather than merely off-brand, and it invites a regulatory
question nobody wants asked.

**Never mention a patient, a case, or a session.** For a company handling
protected health information, patient content in a marketing email is not an
embarrassment, it is an existential problem.

**Never claim a conversation that did not happen.** "You asked for", "as we
discussed", "following up on our call". Having once been a customer is real
shared history, and it is the only shared history we have. Anything warmer than
that is invented.

**Never state a number we cannot source.** No percentages, no hours saved per
month. If we cannot point at where it came from, it does not go in.

**Never print their phone number back at them.** We hold it because they gave
it to us at signup, and they will not remember doing so. Quoting it at someone
who spends their working life on confidentiality reads as surveillance, and
produces "how did you get this" instead of "sure, Tuesday". The email may ask
whether the number ending in those four digits is still the best one. That is
as specific as it is allowed to be.

**Never sound like a machine wrote it.** No em dashes, no hype, no
"revolutionary", no opening paragraph about the state of healthcare. Say one
specific thing about their actual day. Vagueness reads as a mail merge, because
that is exactly what it is.

**Keep it under 120 words**, and sign off like a person.

Every one of those is enforced twice: once as an instruction when the email is
written, and again as a hard check before anything leaves the building. Copy
that trips a check is stopped and put in front of a human, with the exact words
that caused it.

## Dead ends

These are the turns we took and had to reverse. They are here because the
reasoning is the useful part, and because a document that lists only the things
that worked is not describing how anything actually gets built.

**We refused to write to anyone at a hospital, and that was wrong.** The first
version suppressed every clinician at a health system on the grounds that they
cannot buy. "Cannot buy today" is true. "Not worth writing to" does not follow.
Behavioural health clinicians leave institutions for private practice
constantly, and the person who cannot buy this year picks their own tools the
year after. So the institution now changes the message rather than cancelling
it. The old behaviour is still there as a switch, because it is a marketing
judgement rather than a fact, and the argument may go the other way next
quarter. The clinician quoted earlier, the one leaving his health system in
January, would have received nothing under the original design.

**We tried to read the employer off the email address, and it does not work.**
An address ending in .org or .edu tells you the person is not on webmail and
nothing else at all. `med.cornell.edu` is an academic medical centre and
`cornell.edu` is a university, and those are two different organisations with
two different answers. No amount of pattern matching gets you there, because it
is a fact about the world rather than about the string. So the machine looks it
up instead, once per employer. Four thousand clinicians at three hundred
employers costs three hundred lookups once, and nothing ever again.

**Then we assumed the campus told us about the person, which is worse.** A
university address fits a doctoral student in their second year and a professor
of thirty years equally well. Sending the trainee message to the professor is
the single most insulting thing this machine could do. So "still in training"
became a question to be checked person by person rather than an answer. It has
already caught one: the sample includes a Cornell address belonging to a
professor of clinical psychology, and he sits on the not-contacted list instead
of receiving a note about finishing his training.

**We trusted job titles indefinitely.** A lab page from 2019 calling someone a
doctoral candidate is evidence about 2019, and that person is licensed by now.
Everything the research finds is now dated, and anything older than a year
stops counting and goes back on the pile to be checked again.

**We had one signal doing two jobs.** Originally the email address decided both
what the message was about and who it was for, which meant a therapist on Gmail
and a therapist at a practice they own were treated as two different kinds of
clinician rather than the same clinician in different circumstances. Splitting
that into two independent questions is what made the copy stop sounding
generic.

**We used one confidence bar in both directions, and the costs are not
symmetric.** Holding back an email because the research was unsure costs one
missed message. Sending a pitch to a hospital employee because the research was
confidently wrong costs the relationship. So the bar for writing to someone is
high, and the bar for holding back is not.

**We tried to trap the machine into writing bad copy, and it refused.** We
built a list of clinicians engineered to bait invented statistics, hype,
patient detail and false familiarity. The safety checks blocked nothing at all,
because the instructions given up front stop most of it before it is ever
written. That is the right outcome for the product and a bad one for evidence,
since a check that never fires looks identical to no check. So there is a
separate demonstration that feeds real drafts (ones this machine genuinely
produced earlier in the build) through the real checks, and stops six of seven.
The drafts are fixtures. The checks are the live ones.

**One clinician is still unresolved, on purpose.** The research came back
genuinely unsure about a University of Michigan address, because that domain
covers both the campus and, for some staff, the medical school. The machine
declined to guess and put it on the human's list instead. It is sitting in the
review queue right now. Leaving it there is the behaviour we want, not a bug we
missed.

**The self-improvement loop has a real limit, and it is worth saying out
loud.** Every phrase that gets a draft stopped is remembered and forbidden
explicitly on the next run, so the machine does not make the same mistake
twice. But that works by changing the instructions given to the writer. With no
API key configured, the machine falls back to a fixed template, which by
definition cannot learn, and the improvement flatlines. The loop is real. It
just needs the writer to be real too.

## Proving somebody came back

This is the part that has to be built at the moment of sending, or it cannot be
built at all.

Every email carries one identifier, and it travels through all three doors a
clinician can come back through: a link they might click, an address they might
reply to, and the mobile number they might text. All three resolve back to one
person and one send.

The identifier is derived rather than stored, which means it can be rebuilt
from the original list if the record is ever lost, and it gives nothing away if
it turns up in a public URL.

On the last run, five clinicians came back out of the twenty-seven written to,
which is 18.5%. Two clicked, two replied, and one sent a text. The median gap
was four days, and the range ran from one day to nineteen.

One more came back and could not be traced, because they went straight to the
pricing page without touching anything we could recognise. That number is
reported rather than hidden. It is the honest measure of whether the plumbing
holds, it will never be zero, and a report that quietly dropped it would be
worth less than no report at all.

**One caveat, stated plainly.** Reading the real web log, the real inbox and a
real SMS webhook is three integrations that are not built. A sample file stands
in for all three, in the shape they would produce. Point the report at a real
export and nothing else changes.

## What the last run actually did

From a sample list of 33 clinicians:

| | |
|---|---|
| Rows read | 33 |
| Rejected before spending anything, because the data was bad | 3 |
| Deliberately not contacted, each with a stated reason | 3 |
| Written to | 27 |
| Stopped by the safety checks | 0 |
| Left needing a human afterwards | 4 items, about 12 minutes |
| Came back | 5, plus 1 we could not trace |

The three not contacted were the person who asked not to be, the Cornell
professor the research identified as faculty rather than a trainee, and the
Michigan address the research could not settle. Each of those says so, in
writing. The three rejected rows were a malformed email address, a missing name
and a missing mobile number, each reported with its line number so the data can
be fixed.

Run it on a different list and every one of those numbers changes.

## Where one to two hours a month go

The review queue is rewritten on every run, and ordered so the time goes to
judgment rather than triage.

Decisions that are **finished** never appear in the work section. "We looked it
up, and Mayo Clinic employees cannot buy" is a closed question, listed only for
the audit trail. Decisions that are **waiting on a person** are the whole list,
and there are four of them right now.

The hour goes to three things: overruling a researched answer that someone
knows is wrong, settling the addresses the research could not, and reading the
copy that sent but got flagged. Everything else is a lookup against work
already done, which is what keeps the budget intact as the list grows from
thirty-three people to thousands.

## What is real and what is sketched

**Real:** reading the list, both rounds of research and their saved answers,
the routing, the decisions not to send, the writing, the safety checks, the
quarantine of blocked copy, real email over a live connection, the tracking
identifiers and their ledger, the returns report, the review queue, the
metrics, the learning loop, and the schedule.

**Sketched, and marked as such:** the three collectors that would feed real
click, reply and text signals into the returns report; the person-level
research for this sample, because the sample clinicians are invented and
therefore cannot be researched (every simulated record says so in the file);
and SMS as a channel to send on rather than only to be reached on.

**What breaks first if this ran unattended for a month:** the person-level
research going stale. Titles expire, and the one-year rule means old answers
age out into the review queue instead of quietly staying wrong. That is correct
behaviour, but it means the queue grows slowly over time, and the first symptom
is a rising count of things waiting on a human rather than anything visibly
broken.

## What week two looks like

1. **Wire up the three collectors.** The identifiers and the matching are real,
   and the signals feeding them are simulated. This is a day of integration, and
   it turns every number in the impact report from demonstrated to live.
2. **Cadence, and a real second message.** Today, a second run writes to the
   same people. The machine needs to know when it last wrote to someone and what
   it said, so that "stay alive until the timing turns" means a sequence over
   months rather than a repeat.
3. **Use the mobile number.** It is one of the three things we were given, and
   today it does exactly one job: it tells us who texted back. For a rare,
   high-signal message to a clinician who has ignored two emails, that is the
   right channel, and the consent question is answerable.
4. **Feed returns back into targeting.** The report already knows which kind of
   clinician comes back most. Nothing yet uses that to decide who gets written
   to next.

## Run it yourself

You need Python, and to see the machine at its best, an Anthropic API key.

```bash
python3 -m venv .venv         # first time only
source .venv/bin/activate     # every new terminal
pip install -r requirements.txt
cp .env.example .env          # then fill in your keys
python run.py                 # writes drafts to a folder, sends nothing
python run.py --send          # also sends real email
```

**To run it on your own list**, either replace `data/lapsed_clinicians.csv`
with your file and keep the header row, or point at it directly:

```bash
python run.py --input /path/to/your_list.csv
```

It needs four columns: `id`, `name`, `email`, `mobile`. A column called
`do_not_contact` is honoured if it is there. That is deliberately the real
export shape and nothing more, because everything else the copy depends on is
something the machine goes and finds. Hand it a richer file and any column it
carries wins over anything researched.

A second sample list is included so you can watch the answers change:

```bash
python run.py --input data/clinicians_sample_b.csv
```

Everything downstream will differ: the drafts, the blocked copy, the reject
log, the review queue and the metrics.

**To point it at something other than clinicians entirely** (support tickets,
job applicants, dormant accounts) there are four settings at the top of
`config.py` that name which columns mean what. Those are the only places
anything refers to a column by name, and the writing instructions are handed
the whole row, so any column is available to them. No code changes.

### Where things live

| | |
|---|---|
| The list it reads | `data/lapsed_clinicians.csv` |
| Every setting, opinion and rule, in one commented file | `config.py` |
| Drafts it wrote | `out/` |
| Copy it stopped, so you can judge whether it was right | `quarantine/` and `logs/rejects.log` |
| What a human needs to decide | `REVIEW_QUEUE.md` |
| Numbers across every run | `state.json` |
| The one-page recommendation | `WRITEUP.md` |

### Two things worth running once

```bash
python tools/gate_demo.py   # feeds real bad drafts through the real checks
python tools/returns.py     # who came back, through which door, how long after
```

## How AI was used

Claude Code wrote most of this repository under close review. Three things are
worth separating out from that.

The **research on JotPsych and on this audience** was done with web search, and
shaped both the segment briefs and the refusal rules. It is why the prescriber
copy talks about audit exposure rather than time savings.

**One rule came directly out of that research.** JotPsych's own materials claim
a large reduction in documentation time, and a "30 hours per month" figure
circulates alongside it that appears in no company source we could find. The
existing check only caught percentages, so a second one was added for
time-saved claims that carry no percent sign.

**One rule came from reading the machine's own output.** An early draft opened
"You asked for the two figures we've used in marketing", which was a
relationship the machine had invented from nothing. That became its own rule.
It is the loop this whole repository is arguing for: run it, read what came
out, and write the rule.

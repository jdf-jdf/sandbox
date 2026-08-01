# Brand context for the humanizer skill

The skill auto-loads this file from the project root and treats it as an
extension of the chosen `--voice`. Its patterns are the source of several of
the AI-tell rules in `config.REFUSAL_RULES`.

## Who we're writing to

Behavioral health clinicians: psychiatrists, PMHNPs, psychologists,
therapists, counselors. Mostly solo or small private practices. They run
their own businesses, carry licensure risk, and are drowning in notes.

They are not startup people. They do not read tech marketing. The thing
that gets their attention is a specific, accurate description of their
Tuesday evening.

## Voice

`professional`, leaning dry. Peer-to-peer, not vendor-to-lead.

## Banned phrases

Beyond the skill's 43 patterns, never write:

- "revolutionize" / "transform your practice" / "game-changer"
- "unlock" anything
- "seamless" / "effortless" / "frictionless"
- "leverage" as a verb
- "in today's fast-paced healthcare landscape"
- "AI-powered" as a bare adjective (say what it does instead)
- any em dash (absolute rule from the skill)

## Preferred terms

| Don't write | Write |
|---|---|
| providers | clinicians (or the specific credential) |
| patients | depends on segment: prescribers say patients, therapists often say clients |
| solutions / platform | the scribe, the note, JotPsych |
| utilize | use |
| documentation burden | notes, paperwork, charting |

## Things a real clinician would notice

- A therapist doing 50-minute sessions and a psychiatrist doing 15-minute
  med checks have nothing in common workflow-wise. Writing to both at once
  reads as someone who has never met either.
- "Saves you time" is what every vendor says. "Your notes are done before
  your next session starts" is a claim about their actual day.
- Anything that sounds like the software is making clinical decisions is
  disqualifying, not just off-brand.

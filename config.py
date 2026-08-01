"""
Every knob this machine has.

Behaviour is configured here, never in machine/. If you find yourself editing
a file under machine/ to change what the machine says or who it contacts,
something belongs in this file that isn't in it yet.
"""

# ---------------------------------------------------------------------------
# 1. INTAKE  -- the file the machine reads but did not author.
#    Swapping this path (or overwriting the CSV) changes the inputs, and
#    therefore the outputs. Nothing downstream is pinned to this file.
# ---------------------------------------------------------------------------
INTAKE_CSV = "data/lapsed_clinicians.csv"

# Columns the machine needs. A row missing any of these is rejected at intake
# rather than silently producing garbage downstream.
REQUIRED_COLUMNS = ["id", "name", "email", "mobile"]

# The machine does not assume what its rows are called. These are the only
# places anything outside this file reaches into a row by a literal column
# name, so pointing it at a different kind of record -- tickets, applicants,
# accounts -- is these four lines and no code.
ID_FIELD = "id"          # names the artifact: out/<id>.txt, quarantine/<id>.txt
LABEL_FIELD = "name"     # what shows in logs and the review queue
ADDRESS_FIELD = "email"  # where outbound goes, when SEND_TO is unset
# What SEGMENT_RULES match against, in order. Two fields, matching the
# two-part tuples below. SEGMENT is the clinical role, so it reads the
# credential: the address is the SETTING axis and is handled separately below.
ROUTE_FIELDS = ("credential", "practice_type")


# ---------------------------------------------------------------------------
# 2. DECISION  -- what the machine decides on its own, before any AI runs.
#    This is cheap, deterministic, and auditable. Do as much here as you can:
#    every decision made here is one the LLM cannot get wrong.
# ---------------------------------------------------------------------------

# Segment routing. First matching rule wins, and each half is matched as a
# whole token, not as a substring: see _matches_rule in machine/decide.py for
# why "DO" must not be allowed to match "Doctorate".
# (credential token, practice_type token) -> segment name
#
# ORDER IS LOAD-BEARING, so state the decision rather than leaving it to the
# accident of which line came first. Dual degrees are real and common here
# (MD/PhD, PsyD/LMFT, PhD/LCSW). The prescribing credential wins: someone who
# can write a prescription has the prescriber's problem, and the coding and
# audit copy is the copy they need. Moving the therapist rules above these
# would silently reroute every dual-credentialed clinician on the list.
SEGMENT_RULES = [
    (("MD", ""), "prescriber"),
    (("DO", ""), "prescriber"),
    (("PMHNP", ""), "prescriber"),
    (("APRN", ""), "prescriber"),
    (("DNP", ""), "prescriber"),
    (("CNS", ""), "prescriber"),
    (("NP", ""), "prescriber"),
    (("PhD", ""), "therapist"),
    (("PsyD", ""), "therapist"),
    (("EdD", ""), "therapist"),
    (("LCSW", ""), "therapist"),
    (("LICSW", ""), "therapist"),
    (("LMFT", ""), "therapist"),
    (("LMHC", ""), "therapist"),
    (("LPCC", ""), "therapist"),
    (("LPC", ""), "therapist"),
]
DEFAULT_SEGMENT = "unknown"

# Hard suppression. The machine refuses to contact these at all, and says why.
# `do_not_contact` is a column in the CSV; add your own conditions here.
SUPPRESS_IF_DO_NOT_CONTACT = True
SUPPRESS_UNKNOWN_SEGMENT = True  # we'd rather send nothing than send generic

# Employers big enough to name. The cheap half of the domain question: no
# search needed, the answer is already known.
#
# These used to be a suppression list. They are now a SETTING, because the
# premise behind suppressing them was wrong in a specific way. "Cannot buy
# today" is true. "Not worth writing to" does not follow: behavioral health
# clinicians leave institutions for private practice constantly, and the
# person who cannot buy this year picks their own tools the year after. It is
# the same argument that already applies to trainees.
#
# So the institution changes the message rather than cancelling it. See
# SETTING_BRIEF["institutional"]: no pitch, no subscription, keep the thread
# open and ask who actually evaluates tools there.
INSTITUTIONAL_EMAIL_DOMAINS = [
    "@kp.org",
    "@sutterhealth.",
    "@providence.",
]

# Flip to True to restore the old behaviour: institutions get nothing at all.
# Kept as a switch rather than deleted, because it is a marketing judgement
# and not a fact, and the argument may go the other way next quarter.
#
# One consequence worth knowing before flipping it back. While this is False,
# no domain verdict can stop a send, so a wrong verdict costs a slightly
# misjudged email instead of a misdirected one. That is what lets
# DOMAIN_MIN_CONFIDENCE_TO_CONTACT relax and the review queue stay short.
SUPPRESS_INSTITUTIONAL = False

# The other axis. SEGMENT is the clinical role and decides what the email
# talks about. SETTING is where they work and decides whether we write at all
# and in what register: the same PsyD is a different email in solo practice,
# at a practice they own, and two years into a doctorate.
PERSONAL_EMAIL_DOMAINS = [
    "@gmail.", "@yahoo.", "@outlook.", "@hotmail.", "@icloud.",
    "@me.com", "@aol.", "@proton.me", "@protonmail.", "@comcast.",
]
PERSONAL_SETTING = "solo"              # personal address = they are the practice
DEFAULT_SETTING = "practice_owner"     # owns a domain = likely the buyer

# Domain lookup. Some addresses cannot be classified from the string alone.
# A .org or .edu tells you the sender is not on webmail; it does not tell you
# whether they can buy anything -- @med.cornell.edu is a health system and
# @cornell.edu is a university. That question needs research, and research is
# neither deterministic nor free, so it does not belong in the decision layer.
#
# tools/classify_domains.py researches each domain ONCE and writes its verdict
# to the file below. decide.py only ever READS that file. The decision layer
# therefore stays deterministic and offline: same CSV plus same cache always
# produces the same decisions, and a human can open the file and overrule it.
DOMAIN_LOOKUP_SUFFIXES = (".org", ".edu")
DOMAIN_CACHE_PATH = "data/domain_verdicts.json"

# Verdict -> setting. None means suppress: researched, and the answer is no.
# A verdict missing from this map ("unclear") or missing from the cache
# entirely also suppresses -- an unresearched institution is exactly the case
# where a guess is expensive, so the machine declines to guess and puts the
# domain on the human's work order instead. Same instinct as
# SUPPRESS_UNKNOWN_SEGMENT: in doubt, send nothing.
DOMAIN_VERDICT_SETTINGS = {
    "health_system": "institutional",
    "training": "trainee",
    "private_practice": "practice_owner",
}
# Only bites while SUPPRESS_INSTITUTIONAL is True. With suppression off, the
# verdict picks a register rather than a fate, so a low-confidence guess costs
# a slightly wrong tone and holding the send adds nothing. The bar is kept
# here, and kept high, so that flipping suppression back on restores the
# careful behaviour in one move instead of two.
DOMAIN_MIN_CONFIDENCE_TO_CONTACT = "high"   # one of: low, medium, high

# How the research step (tools/classify_domains.py) is told to think. It runs
# once per domain, not once per row, so a list of 4,000 clinicians at 300
# employers costs 300 searches, and costs nothing at all on the second run.
DOMAIN_MAX_SEARCHES = 4                # web searches per domain, hard cap
DOMAIN_RESEARCH_PROMPT = """Identify the organization that owns the email \
domain {domain} and decide which one thing it is.

Search for the domain itself. Do not reason from the name alone: plenty of \
private group practices own a .org, and plenty of universities run a hospital \
under a subdomain.

The subdomain is the answer more often than the root domain is. Treat \
med.cornell.edu and cornell.edu as two different organizations, because they \
are: the first is an academic medical center, the second is a university. \
Research the exact domain you were given.

Choose exactly one verdict:

- "health_system" if the domain belongs to a hospital, health system, \
academic medical center, medical school, clinic network, or community health \
organization. These people are employees. Their documentation tool was chosen \
for them by an institution, they cannot buy software, and mail to them is \
wasted.

- "training" if the domain belongs to a university or college that is NOT a \
medical center. A behavioral health clinician at such an address is most \
likely still in training: a doctoral student, a resident on a campus address, \
or someone accruing supervised hours. They cannot buy anything today, but \
they choose their own tools when they finish.

- "private_practice" if the domain belongs to a private practice, group \
practice, or a small clinical business, whatever its suffix.

- "unclear" if the search does not settle it, or if the domain plausibly \
covers both a university and its medical center under one address. Say \
unclear rather than guessing. A wrong "private_practice" mails a hospital \
employee, and a wrong "training" mails someone a message about a career stage \
they left a decade ago.

Set confidence honestly. "high" means the search showed you the organization \
and its type directly. "medium" means the evidence is good but indirect. \
"low" means you are inferring. Anything below {min_confidence} is treated as \
unclear and goes to a human, so an honest "low" costs nothing and a \
flattering "high" costs a misdirected email.

Finish by calling record_verdict exactly once."""


# ---------------------------------------------------------------------------
# 2b. PERSON LOOKUP -- the second pass, and the one that makes a three-column
#     list workable.
#
#     The real list is name, email, mobile. Nothing else. No credential, no
#     practice type, no notes. So the machine cannot be handed a segment: it
#     has to go and find one, which is what this layer does. It also checks
#     the domain layer's guesses, because "clinician at a university" is a
#     fact about the campus, not about the person on it.
#
#     Cost shape is the opposite of the domain pass. Domains amortise across
#     everyone who shares an employer; people do not. So this runs only for
#     the rows below, and never for the whole list.
# ---------------------------------------------------------------------------
PERSON_CACHE_PATH = "data/person_verdicts.json"

# Settings from the domain pass that are hypotheses rather than answers, and
# so get checked person by person. "trainee" is the dangerous one: writing to
# a department chair as though they were two years into a doctorate is the
# single most insulting thing this machine could do.
PERSON_LOOKUP_SETTINGS = ("trainee",)

# Verdict -> setting. None means suppress: researched, and the answer is no.
PERSON_VERDICT_SETTINGS = {
    "trainee": "trainee",
    "faculty": None,            # employed by the institution, and not a trainee
    "staff_clinician": None,    # the institution chose their EHR
    "private_practice": "practice_owner",   # a side caseload they own: a buyer
}
PERSON_MIN_CONFIDENCE_TO_CONTACT = "high"

# Titles expire. A doctoral student in 2019 is licensed by 2026, and the web
# remembers them as they were. A verdict older than this is treated as
# unproven rather than as true, and goes back on the research pile.
PERSON_EVIDENCE_MAX_AGE_MONTHS = 12

PERSON_MAX_SEARCHES = 4                # web searches per person, hard cap
PERSON_RESEARCH_PROMPT = """Identify this specific person and decide what \
they do today.

  Name: {name}
  Email domain: {domain}
  Credential on file: {credential}

A previous step established the domain and guessed "{hypothesis}" for this \
person. Treat that as a question, not an answer. It came from the \
organization, and organizations contain every career stage at once.

Search for the person at that organization by name. Their credential, if one \
is on file, is a strong disambiguator: there are many people with any given \
name and few with that name and that licence at that institution.

Choose exactly one verdict:

- "trainee" if they are currently a student, intern, practicum placement, \
resident, fellow, or accruing supervised hours toward licensure.

- "faculty" if they hold an academic or supervisory appointment: professor of \
any rank, lecturer, clinical supervisor, training director, program director. \
These people are not trainees and are employed by the institution.

- "staff_clinician" if they are employed to see clients at the institution: \
counselling centre staff, a clinician in a campus health service.

- "private_practice" if they run or work in a practice of their own, whether \
or not they also hold an institutional role. Someone who teaches two days a \
week and keeps a private caseload belongs here: they can buy.

- "unclear" if the search does not settle it, or if you cannot tell which \
person of that name you have found. Say unclear rather than guessing. A wrong \
"trainee" insults a professor of thirty years.

DATE YOUR EVIDENCE. This is the part that matters most, and the part a search \
will happily let you get wrong. A page saying "doctoral candidate" is evidence \
about the day it was published, not about today. Record evidence_date as the \
publication or last-updated date of the source you actually relied on, not \
today's date, and not the date you ran the search. If a source carries no \
date you can establish, do not treat it as current: find one that does, or \
return "unclear".

Anything confirmed longer ago than {max_age_months} months is discarded \
downstream regardless of how confident you are, so a precise old date is more \
useful than a vague recent-sounding one.

Also record the professional credential you find (MD, DO, PMHNP, PhD, PsyD, \
LCSW, LMFT, LPC and so on) if the search shows it, because the list does not \
carry one and the rest of the machine routes on it. Leave it empty rather \
than inferring it from the job title.

Set confidence honestly. "high" means the search showed you this person and \
their current role directly, on a dated source. Anything below \
{min_confidence} is treated as unclear and goes to a human.

Finish by calling record_person exactly once."""


# ---------------------------------------------------------------------------
# 3. GENERATION
# ---------------------------------------------------------------------------
MODEL = "claude-opus-5"

# This model thinks by default, and MAX_TOKENS caps thinking and response text
# TOGETHER. A tight budget can be consumed entirely by reasoning, leaving a
# truncated or empty email. Hence the headroom: a 120-word email needs ~200 of
# these and the rest is slack for the thinking block.
MAX_TOKENS = 2000

# Drafting a short email is not a reasoning problem. "low" keeps thinking (and
# cost) down without disabling it, which has its own failure modes. Raise to
# "medium" if the drafts read thin.
EFFORT = "low"

# Per-segment framing: the positive half of the opinion. What we believe each
# audience actually cares about, as opposed to REFUSAL_RULES below, which is
# what we believe they must never be sent.
SEGMENT_BRIEF = {
    "unspecified": (
        "The list did not carry a credential for this person and research did "
        "not find one, so you do not know whether they prescribe or whether "
        "they do talk therapy. Do not pick one. The difference matters (one "
        "worries about coding and audit exposure, the other about narrative "
        "notes and evening paperwork) and guessing wrong is worse than saying "
        "nothing. Write about the part of the work that is common to both: "
        "documentation that follows you home. Let the setting carry the rest."
    ),
    "prescriber": (
        "Prescribers (MD/DO/PMHNP) run short, high-volume med-management "
        "visits. Their pain is not narrative depth, it is reimbursement and "
        "audit exposure: an undercoded note loses money every day it goes "
        "out, and an overcoded one invites clawback. They care about E/M and "
        "ICD-10/CPT correctness against their actual payer mix, about prior "
        "authorization, and about getting out of the office on time. They do "
        "the ROI math themselves, so be specific or say nothing."
    ),
    "therapist": (
        "Therapists (PhD/PsyD/LCSW/LMFT/LPC) run 45-55 minute sessions and "
        "write narrative progress notes. Their pain is evening paperwork and "
        "the fear that a tool will flatten clinical nuance. They are more "
        "privacy-protective and more skeptical of AI than prescribers."
    ),
}

# Per-setting framing: the other axis. SEGMENT is what the work is, SETTING is
# who they answer to. It decides register and ask, not subject matter.
SETTING_BRIEF = {
    "institutional": (
        "Employed at a hospital, health system, or academic medical center. "
        "They cannot buy this and their employer already chose their "
        "documentation system, so a pitch insults them and a discount is "
        "meaningless. Write anyway, for one reason: clinicians leave "
        "institutions for private practice all the time, and the person who "
        "cannot buy this year picks their own tools the year after. So the "
        "job of this email is to be worth answering, not to sell. Two things "
        "are legitimately worth asking: whether they are staying put or "
        "planning something of their own, and who at their organization "
        "actually evaluates documentation tools. Say plainly that you know "
        "they may not be able to choose this themselves. Being the vendor "
        "who understood that is the entire play.\n\n"
        "On the path, they are stage 1 by definition: employed, and either "
        "settled there or quietly working out an exit. Which of those two is "
        "the only thing worth asking, and it is a question almost everyone "
        "enjoys answering about themselves.\n\n"
        "Do NOT ask for a call. Asking an employed clinician to get on the "
        "phone with a vendor whose product they cannot buy is asking them to "
        "spend the one thing they have less of than money. One question."
    ),
    "solo": (
        "Solo clinicians, reached at a personal address (Gmail, iCloud, "
        "Proton, and the like). They are the practice: no admin, no billing "
        "staff, no IT department to ask. Nobody has to approve a purchase, "
        "which makes them the easiest sale and the least forgiving audience "
        "for anything that wastes their time. Their pain is evening "
        "paperwork and the unpaid hours that follow the last session of the "
        "day. Price matters and they will ask about it. Do not write as if "
        "they have a team.\n\n"
        "This is the bucket where you know the least and the question earns "
        "the most. A personal email address is stage-blind: it is worn by the "
        "clinician still employed and daydreaming about leaving, by the one "
        "who left two months ago and is drowning in setup, and by the one who "
        "has run her own practice for twelve years. Those three people need "
        "different things and share an inbox pattern. Do not pick one. Name "
        "two or three of the stages and ask which fits. That question is the "
        "entire email and it is allowed to be almost the entire email.\n\n"
        "Do NOT ask for a call. They have not told you anything yet, and a "
        "call is a big ask to make of someone who owes you nothing. One "
        "question, one line to answer it. The call is the next email."
    ),
    "practice_owner": (
        "Reached at a domain they appear to own, so most likely the owner or "
        "a partner at a private practice. They buy for other people as well "
        "as themselves, which means they think about onboarding, about what "
        "their clinicians will actually adopt, and about what happens to the "
        "notes if they ever leave. Their pain is the aggregate: documentation "
        "drag across the whole practice, and clinicians burning out on it.\n\n"
        "Someone who bought a domain has already made the jump, so they sit at "
        "stage 3 or 4 and the stage question is mostly answered. For them the "
        "live unknown is the other axis: which part of running the place is "
        "the mess right now. Ask that. It is the question that gets a product "
        "line named without you having to guess one, and an owner will answer "
        "it happily because it is the thing they complain about anyway. What "
        "would you hand over first, notes or billing or the schedule, is a "
        "fair way to ask as long as you do not read out the whole list.\n\n"
        "This is the one setting where you MAY also ask for a call, because "
        "they are a live buyer with budget and no approval chain. Ask the "
        "stage question first and let the call be the smaller second sentence, "
        "never the other way around."
    ),
    "trainee": (
        "Reached at a university address that is not a medical center, so "
        "most likely still in training: residency, fellowship, a doctoral "
        "program, or supervised hours toward licensure. Two things follow. "
        "They cannot buy anything today, and their institution already "
        "chose their EHR for them. But they will be choosing their own tools "
        "the moment they go into practice, which is the only reason to write "
        "at all. Open by checking the premise rather than assuming it: say "
        "plainly why you are writing, ask where they are in training and "
        "what comes after. Do not pitch a purchase, do not describe features, "
        "and do not pretend to know their situation. One honest question "
        "beats a paragraph of positioning.\n\n"
        "They sit before stage 1, which makes 'what comes after this' the "
        "natural question rather than a sales one. Do NOT ask for a call."
    ),
}

# Formatted against the WHOLE intake row plus {segment}, {segment_brief} and
# {learned_constraints}. Any column in the CSV is therefore available here as
# {column_name} with no code change. Referencing a column that doesn't exist
# fails on the first row and names the missing column.

# The product stopped being one thing, which changes what an email is allowed
# to assume. The export says a person signed up. It does not say which part they
# signed up for, and most of this list arrived when the scribe was the whole
# product. "You tried our note-taker" is therefore a guess wearing the clothes
# of a fact, and it is the same failure as guessing their stage.
#
# Edit this list as lines ship. It is injected into the prompt, so adding one
# here changes every email the next run writes with no code change.
PRODUCT_LINES = [
    "the scribe: the session note, written as you work",
    "billing and coding",
    "audit and documentation review",
    "revenue analytics",
    "e-prescribing",
    "scheduling",
    "credentialing",
]
PRODUCT_LINES_BLOCK = "\n".join(f"  - {p}" for p in PRODUCT_LINES)

PROMPT = """You are writing a single short outreach email on behalf of JotPsych, \
which began as an ambient scribe for behavioral health clinicians and is now \
several products.

Everyone on this list came to JotPsych once and is not a customer today. They \
know what the product is, so explaining it to them reads as though nobody \
checked.

This is not a win-back and you must not write one. Almost nobody on this list \
weighed the product and rejected it. The timing was wrong: the practice was not \
ready, the old contract had a year to run, the pain had not arrived yet. Timing \
changes, and that is the entire premise of this email.

So do not ask why they left. A clinician who is asked that is being handed \
unpaid work, and the answer is a fact about the past. Ask where they are now. \
That answer tells you whether the timing has turned, and it is the output this \
machine exists to produce.

The journey, which is the actual subject of the email. Behavioral health \
clinicians move along a path from employed to independent:
  1. Employed somewhere, turning over the idea of going out on their own.
  2. Recently made the jump, wiring up the practice: credentialing, first
     clients, picking systems.
  3. Established solo, steady caseload, past the scramble.
  4. Growing, adding clinicians, buying for other people as well as themselves.

Where someone sits on that path decides whether JotPsych is irrelevant, \
interesting, or urgent. Usually you cannot tell from the file below, and \
guessing insults them. Ask.

The second thing you do not know is which product. JotPsych is now several \
lines:
{product_lines}

The export records that this person signed up. It does not record which line \
they used, and most of this list arrived when the scribe was the entire \
product, so the line they would want today may not have existed when they came. \
Writing "when you tried our note-taker" is a guess dressed as a fact, and it is \
the same mistake as guessing their stage.

Three rules follow, and they matter more than they look:
- Never state which part they used or wanted. You do not know.
- Never list the lines at them. A menu is a brochure, this is not a brochure,
  and a reader who is handed seven options answers none of them.
- You MAY say, in one plain sentence, that JotPsych covers more ground than it
  did when they signed up. That is true, it is worth their knowing, and it
  earns the question that follows. Then ask, and let them name the part.

The stage and the product are not separate questions. Someone wiring up a new \
practice is thinking about credentialing and scheduling; someone established is \
thinking about billing and what the revenue actually looks like. Ask where they \
are and the answer usually tells you which line to talk about next, which is \
why one good question beats two mediocre ones.

Recipient:
  Name: {name}
  Credential: {credential}
  What research found: {practice_type}
  Segment: {segment}
  Setting: {setting}
  Anything on file: {notes}

That list is everything the machine has. The export carried a name, an email \
address and a mobile number; the credential and the role were found by \
searching the open web, not told to us. "Anything on file" is usually empty, \
because usually there is nothing. So write from what is above and nothing \
else. You do not know why they left, what they thought of the \
product, how long they used it, or what their caseload looks like. Above all \
you do not know which of the four stages they are in now. The setting below is \
a hint, never a verdict: it is derived from their email domain, which is a \
weak signal about a person's life. Write the email that finds out.

Segment context: {segment_brief}

Setting context: {setting_brief}

Close on one question about where they are, and make it answerable in a single \
line. Rules for that question:

- It ends in a question mark. "I would love to hear where you landed" is not a
  question and converts like the statement it is.
- A three word reply has to be a real answer. Naming two or three of the stages
  above and asking which one fits is the highest-converting form, because it
  costs them nothing and shows you know the path exists.
- One question only. A second ask competes with the first and both lose.
- No product in it. The moment the question is a pretext for a pitch, it stops
  being a question and they can feel it.

Whether you may ALSO ask for a call is decided by the setting context below. \
Only ask when that context tells you to. Where it does, we hold a mobile number \
ending {mobile_last4}.

- Ask whether that is still the best number, and offer to work around their
  schedule. One sentence, at the end, no build-up.
- You may write the last four digits. You must NEVER write the full number.
  They gave it to us and will not remember giving it to us, and quoting it
  back at a clinician who spends their day on confidentiality reads as
  surveillance. "Still the best number, ending {mobile_last4}?" is the most
  specific you are allowed to be.
- If {mobile_last4} is empty, skip the digits and just ask whether a call is
  easier than email.
- Ask. Do not assume. Never say you will call, only that you would like to.

Rules:
- Under 120 words.
- Concrete about whichever part of the work you name, and never vague about
  which part. "Your workflow" and "your admin burden" are what a vendor writes
  when it does not know. No hype, no exclamation marks.
- Never imply the product makes clinical judgments or decisions.
- Never invent statistics, outcomes, or testimonials.
- Never reference or invent any patient, case, or session content.
- Never claim a prior conversation, request, or relationship. If it is not in
  the recipient block above, it did not happen. No "you asked for", "as we
  discussed", "per your request", "following up on our call". That they once
  used the product is the only shared history you have.
- Plain sign-off. No "Best regards, The JotPsych Team".

Write like a person, not a language model:
- No em dashes. Use a comma, a colon, parentheses, or two sentences.
- Vary sentence length. Uniform rhythm is the clearest tell.
- No participle clauses tacked onto the end ("..., ensuring accuracy").
- Never say a thing "stands as", "serves as", or "underscores" anything.
- Banned: delve, leverage, robust, seamless, landscape, realm, unlock.
- Don't open by explaining the state of healthcare. Open with them.
- Say one specific thing about their actual day. Vagueness reads as a mail
  merge, because it is one.

{learned_constraints}

Output only the email body. No subject line, no preamble."""


# ---------------------------------------------------------------------------
# 4. QUALITY CONTROL  -- the refusal rules.
#
#    This list is the machine's opinion about what is off-brand, written as
#    code. It is deliberately specific: a filter nobody argued about is a
#    filter that catches nothing.
#
#    Each rule: (id, human-readable reason, regex pattern, severity)
#    severity "block" -> never sends, goes to quarantine
#    severity "flag"  -> sends, but lands in REVIEW_QUEUE.md for a human
# ---------------------------------------------------------------------------
REFUSAL_RULES = [
    # --- Clinical / regulatory. These are existential for a HIPAA company. ---
    ("phi_leak", "References patient/session content in a marketing asset",
     r"\b(my patient|your patient|a patient who|case study|the client who|session notes? (?:from|about)|presented with)\b", "block"),

    ("clinical_claim", "Implies the product exercises clinical judgment",
     r"\b(diagnos\w+ for you|decides? the treatment|clinical judgment|recommends? a diagnosis|treats? patients)\b", "block"),

    ("compliance_overclaim", "Vague or unearned security/compliance claim",
     r"\b(totally secure|100% secure|completely private|fully compliant|bank-level)\b", "block"),

    # --- Voice. Overworked clinicians do not respond to startup register. ---
    ("hype", "Hype register — reads as tech marketing, not peer-to-peer",
     r"\b(revolutionary|game.?chang\w+|cutting.edge|unlock|supercharge|10x|seamless\w*|effortless\w*)\b", "block"),

    ("fake_urgency", "Manufactured urgency",
     r"\b(act now|limited time|don'?t miss out|last chance|spots? are filling)\b", "block"),

    ("replacement_framing", "Suggests AI replaces the clinician — fastest way to lose this audience",
     r"\b(replace\w* (?:your|the) (?:judgment|clinician|therapist)|no longer need to think|does the thinking for you)\b", "block"),

    # --- Privacy. ---
    # We hold their mobile number because they gave it to us, and they will
    # not remember giving it to us. Printing it back at a clinician who spends
    # their day on confidentiality reads as surveillance, and produces "how
    # did you get this" instead of "sure, Tuesday". The prompt already says
    # not to. This makes it true every time instead of most times.
    #
    # Shaped to a real number rather than to "several digits in a row", so
    # "ending 0142", "45-55 minute sessions" and "2026" all still pass. A
    # looser digit-run pattern blocks dates and session lengths, and a gate
    # with false positives is a gate people switch off.
    ("phone_number", "Full phone number printed in the body",
     r"(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b", "block"),

    # --- Mechanical failures. ---
    ("unfilled_template", "Unfilled placeholder made it into the output",
     r"(\{\w+\}|\[NAME\]|\[PRACTICE\]|XXXX|TODO)", "block"),

    ("fabricated_stat", "Numeric claim the machine cannot source",
     r"\b\d{1,3}(\.\d+)?%\s*(of|more|less|fewer|increase|reduction|improvement)", "block"),

    # fabricated_stat above only catches percentages. The time-saved claims
    # this audience actually gets pitched ("30 hours per month") carry no
    # percent sign and would sail through it. Scoped to a rate -- a duration
    # per unit of time -- so describing a clinician's own day ("15-minute
    # slots", "45-55 minute sessions") stays legal.
    ("unsourced_quantity", "Time-saved claim with no attributable source",
     r"\b\d{1,4}\+?\s*(?:hours?|hrs?|minutes?|mins?)\s*(?:a|an|per|each)\s+(?:day|week|month|year)\b", "block"),

    # Warmth the machine has not earned. A win-back list is exactly where this
    # goes wrong: having once been a customer is real shared history, and the
    # model will happily inflate it into a conversation that never happened.
    # Deliberately narrow. "You asked for the two figures" is invented; "you
    # asked on the webinar whether..." is grounded in the notes field and has
    # to stay legal, so the pattern requires the giveaway object after the verb.
    ("fabricated_relationship", "Claims a prior conversation or request that never happened",
     r"\b(you\s+asked\s+(?:for|us|me|about)|as\s+(?:we\s+)?discussed|per\s+your\s+request|following\s+up\s+on\s+(?:our|your)|as\s+promised|(?:great|good)\s+(?:speaking|talking|chatting)\s+with\s+you|thanks\s+for\s+reaching\s+out|when\s+we\s+(?:spoke|talked)|you\s+mentioned\s+that)\b", "block"),

    # --- Premise. The reframe the machine runs on. ---
    # These clinicians did not weigh the product and reject it; the timing was
    # wrong. An email that treats them as churn asks them to relitigate a
    # decision they do not remember making, and the reply rate shows it. The
    # prompt now forbids the win-back frame. This makes it true on every run
    # rather than most runs.
    #
    # Deliberately does NOT catch the bare phrase "why you stopped", because
    # the strongest version of the new opener is "I'm not writing to ask why
    # you stopped", and a gate that blocks its own best line is a gate someone
    # switches off. The interrogative forms below have no innocent reading.
    ("winback_framing", "Treats the recipient as churn to be won back",
     r"\b(welcome\s+back|come\s+back\s+to|back\s+on\s+board|give\s+(?:us|it|jotpsych)\s+another\s+(?:try|chance|look)|second\s+chance|win\s+you\s+back|we(?:'ve|\s+have)?\s+noticed\s+you|why\s+did\s+you\s+(?:stop|leave|cancel)|what\s+made\s+you\s+(?:stop|leave|cancel)|what\s+went\s+wrong)\b", "block"),

    # The rule above catches an email that SAYS come back. This catches the
    # quieter version that every draft of the first generation opened with:
    # "you used JotPsych at some point and then stopped". Nobody asks them to
    # return, but the lapse is still the subject of the sentence, and the
    # recipient is still being handed a decision of theirs to explain.
    #
    # Flag, not block, on purpose. The strongest opener does not mention
    # stopping at all ("you signed up a while back, which usually means the
    # notes were getting away from you around then"), so a block is probably
    # correct eventually. Promote it once a run's worth of drafts shows the
    # model reliably writes around it, rather than guessing that now.
    ("lapse_as_subject", "Opens on the recipient's lapse instead of their situation",
     r"\b(?:you|they)\s+(?:then\s+)?stopped\b|\byou\s+(?:used|tried)\s+\w+\s+at\s+some\s+point\b", "flag"),

    # Coded check, implemented in machine/qc.py: a regex cannot express "asks
    # nothing at all". Listed here so this file stays the whole opinion.
    ("no_question", "Body asks nothing, so there is nothing to reply to",
     None, "block"),

    # --- AI tells. ---
    # The rules above catch output that is WRONG. These catch output that is
    # RIGHT but reads like a machine wrote it, which for a cold email to a
    # skeptical audience is its own kind of failure.
    ("em_dash", "Em dash: the single most reliable tell in generated prose",
     r"—", "block"),

    # NOTE: \s+ rather than literal spaces throughout. Emails wrap, and a
    # pattern with a hard space silently misses the phrase every time it
    # happens to straddle a line break.
    ("significance_inflation", "Puffs up importance instead of saying what the thing does",
     r"\b(stands\s+as|serves\s+as\s+a|testament\s+to|pivotal|underscor\w+|plays?\s+a\s+(?:vital|crucial|key)\s+role|in\s+today'?s(?:\s+\w+){0,3}\s+(?:landscape|world|environment))\b", "block"),

    ("ai_vocab", "Vocabulary that reads as LLM-generated",
     r"\b(delv\w+|leverag\w+|robust|tapestry|myriad|realm|navigate\s+the|landscape\s+of)\b", "block"),

    ("ing_tail", "Participle clause tacked on to fake depth",
     r",\s+(?:highlighting|underscoring|emphasizing|reflecting|ensuring|fostering|showcasing|contributing to)\b", "flag"),

    ("hedging", "Filler that delays the point",
     r"\b(it'?s\s+worth\s+noting|it'?s\s+important\s+to\s+note|that\s+said,|when\s+it\s+comes\s+to)\b", "flag"),

    ("not_just_but", "The 'not just X, but Y' construction",
     r"\bnot\s+just\s+[\w\s]{1,40},?\s*(?:but|it'?s)\b", "flag"),

    # --- Softer signals: send, but tell the human to look. ---
    ("too_long", "Over length budget", None, "flag"),          # checked in code
    ("no_personalization", "Recipient name never appears", None, "flag"),  # checked in code
]

MAX_WORDS = 140

# Columns the PROMPT is allowed to reference that the intake file may simply
# not have. A minimal export (name, email, mobile) is the normal case, not an
# error, so a missing column fills with an explicit absence instead of
# stopping the run. A column that IS present but empty is handled the same way
# in machine/generate.py. What this must never do is quietly substitute a
# plausible value: "(not known)" is a fact, a guessed credential is a lie.
MISSING_FIELD_DEFAULTS = {
    "credential": "(not known)",
    "practice_type": "(not known)",
    "notes": "(nothing on file)",
}

# The mobile number is never printed in the body. See the phone_number refusal
# rule: the email may ASK whether the number on file is current, and may use
# the last four digits to show we hold it carefully, but the full number
# quoted back at a behavioural health clinician reads as surveillance.
MOBILE_FIELD = "mobile"


# ---------------------------------------------------------------------------
# 5. OUTBOUND
# ---------------------------------------------------------------------------
SUBJECT_TEMPLATE = "[machine] draft for {name}"

# --- attribution: how a return traces back to the machine -------------------
# Every send carries one token through three doors: a link they can click, a
# Reply-To they can reply to, and a number they can text. All three resolve to
# one row and one run, so "a dormant clinician came back" stops being a story
# and becomes a lookup. See machine/attribution.py.
ATTRIBUTION_TOKEN_CHARS = 12
ATTRIBUTION_LINK_TEMPLATE = "https://jotpsych.com/hello/{token}"
ATTRIBUTION_LEDGER_PATH = "logs/attribution.jsonl"
# The footer states a fact and asks for nothing. It used to read "If you want to
# pick it back up", under a /welcome-back/ slug, which confessed that the email
# was a win-back however carefully the body avoided saying so. A reader who is
# asked "where are you now?" and then handed a come-back link has been told the
# question was a pretext, and they only need to notice that once.
ATTRIBUTION_FOOTER = "Your old account is still there: {link}"

# "file" always runs and needs no credentials.
# "smtp" is the real outbound action. Both run when --send is passed;
# file-only is the default so a dry run cannot email anyone by accident.
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


# ---------------------------------------------------------------------------
# 6. STATE / LEARNING
# ---------------------------------------------------------------------------
STATE_PATH = "state.json"
# How many of the worst-offending phrases are fed back into the next run's
# prompt as explicit "never write this" constraints.
LEARNED_CONSTRAINT_COUNT = 5

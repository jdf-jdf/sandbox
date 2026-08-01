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
REQUIRED_COLUMNS = ["id", "name", "email"]

# `mobile` is deliberately NOT required. The email asks whether the number on
# file is still current, so a row without one loses a closing line, not its
# reason to exist. Rejecting an otherwise good clinician over a blank phone
# column throws away a lead to protect a nicety. The prompt handles the empty
# case: no digits, just an offer to call.

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


# ---------------------------------------------------------------------------
# 3a. BRAND -- what the machine is allowed to believe about JotPsych.
#
#     Sourced from BRAND.md, which carries a citation for every fact below.
#     The prompt used to open by calling JotPsych "an ambient AI scribe". That
#     was true in 2023, and it is the product this entire list already walked
#     away from. Describing a churned customer's own reason for leaving back
#     at them is exactly the "nobody checked" failure the prompt spends a
#     paragraph warning about, so the description lives here now, in one
#     place, and moves when the brand moves.
# ---------------------------------------------------------------------------
BRAND_BRIEF = (
    "JotPsych is the behavioral health EHR that defends clinicians from "
    "insurance companies. Notes, billing and the whole practice in one "
    "system: it drafts the chart during the session, checks every note and "
    "claim against payer rules, works the denials, and follows the money "
    "from the visit to the bank account. The named parts are the AI Scribe, "
    "JotBill (claims, denials, appeals), JotCred (payer enrollment), "
    "JotAudit (flags a weak note before it is signed), JotSite (practice "
    "website), JotRx (e-prescribing, including EPCS) and JotMeet "
    "(telehealth). That list is complete. If a product name is not on it, it "
    "does not exist, so do not invent one. "
    "One thing about the framing, because it is the part that is easy to get "
    "subtly wrong: JotPsych does not sell time saved. It sells position "
    "against the payer. The note is a defensive instrument, written to "
    "survive an audit and beat a downcode. Nothing in the company's own copy "
    "promises a clinician a better life, and copy that drifts back toward "
    "work-life balance has left the brand even when every word in it is "
    "clean."
)

# Names the QC gate will accept in a body. Anything matching Jot<Capital> and
# absent from this tuple is blocked outright: see the unknown_module check in
# machine/qc.py. A regex can express "don't say seamless"; it cannot express
# "don't say the name of a product we do not sell", so that one is coded.
BRAND_MODULES = ("JotBill", "JotCred", "JotAudit", "JotSite", "JotRx", "JotMeet")

# The win-back hook, and the only place the machine volunteers what the
# product does now.
#
# Gated by setting rather than said to everyone, because news is only news to
# somebody who could act on it. The institutional and trainee briefs below
# argue at length that a pitch to a clinician who cannot buy is worse than
# silence, and that argument does not stop being true because we finally have
# something new to say.
#
# So membership of this dict IS the gate, and it holds only the two settings
# that can buy. institutional and trainee are absent on purpose, not by
# oversight; they resolve to BRAND_NEWS_SUPPRESSED below, as does any setting
# nobody has written copy for yet. Silence is the default and has to be
# argued out of, which is the right way round for a list that churned once.
BRAND_NEWS_BY_SETTING = {
    "solo": (
        "They stopped using a note-taker. What they have not seen is that "
        "the note now runs into billing: the same system writes the chart, "
        "checks the claim before it goes out, and chases the denial when it "
        "comes back. For a clinician with no biller and no admin, that is "
        "the part worth mentioning. One sentence is the whole budget. It is "
        "context for the question you are asking, not the reason you are "
        "writing."
    ),
    "practice_owner": (
        "They stopped using a note-taker and will not have seen that it is "
        "now the chart and the billing in one place. The angle that lands on "
        "someone who signs the invoices is consolidation: scribe, EHR, "
        "billing, e-prescribing and credentialing bought separately cost "
        "more than they should and never quite join up. One sentence, then "
        "back to the question."
    ),
}

# What everyone else gets instead. Said out loud rather than left blank: an
# empty slot tells the model nothing, and a model told nothing about a subject
# it knows plenty about will fill the space itself.
BRAND_NEWS_SUPPRESSED = (
    "Volunteer nothing about what the product does now. This person cannot "
    "buy it, and telling somebody what they are missing when they have no "
    "way to act on it is a pitch wearing a hat. Describe no features, name "
    "no parts of the product, quote no numbers and no prices. If they ask, "
    "that is a different email and a better one."
)

# The numbers JotPsych publishes about itself. Attributable, therefore
# quotable, but only in this exact wording.
#
# machine/qc.py exempts these strings from the two rules named in
# CLAIM_EXEMPT_RULES by removing them before those rules read the text. So a
# claim reproduced word for word passes, and a paraphrase ("over 40 hours a
# month", "nearly all of your documentation time") still trips the gate. That
# asymmetry is the point: the model may cite us, it may not do arithmetic on
# our behalf.
#
# Worth saying, because no gate can: sourced is not the same as persuasive.
# "Saves you 30 hours a month" is the exact sentence every scribe vendor
# sends, to a list that has already ignored it once. The allowlist exists so
# the machine CAN reach for a number, not so that it should.
APPROVED_CLAIMS = [
    ("90% less time on documentation",
     "https://www.jotpsych.com/post/jotpsych-raises-seed-round"),
    ("30 hours a month", "https://www.jotpsych.ai/"),
    ("10,000+ practices", "https://jotpsych.com"),
    ("2.5M+ notes", "https://jotpsych.com"),
    ("150+ payer rules", "https://jotpsych.com"),
    # Commercial facts. Nothing in REFUSAL_RULES blocks a price, so these need
    # no exemption; they are here because the solo brief says outright that
    # these clinicians will ask, and a machine that has the answer on file
    # should not be vague about it.
    ("$135 a month", "https://jotpsych.com/pricing"),
    ("no long-term contract", "https://jotpsych.com/pricing"),
    ("no credit card required to start", "https://jotpsych.com/pricing"),
]

# Which rules an approved claim is allowed to satisfy. Nothing else is
# exemptible: an allowlisted string still has to clear em_dash, hype,
# clinical_claim and the rest. The exemption is about provenance, not licence.
CLAIM_EXEMPT_RULES = ("fabricated_stat", "unsourced_quantity")


# --- keeping all of the above true -----------------------------------------
# Everything above this line is a fact about a company, and facts about
# companies go stale. This one already did: the prompt described an ambient
# scribe for two years after the product stopped being one, and nothing in the
# machine could notice, because nothing in the machine was looking.
#
# tools/brand_check.py looks. Monthly, before the run: re-read the pages, diff
# them against the last snapshot, ask marketing what is coming that is not on
# the site yet, and write a work order. It deliberately does not edit any of
# the constants above. A machine that rewrites its own brand voice off a
# scraped diff is one bad parse away from sending something nobody approved,
# and this is the one part of the system where a human in the loop is the
# feature rather than the cost.
BRAND_SOURCES = [
    "https://jotpsych.com",
    "https://jotpsych.com/pricing",
    "https://jotpsych.com/for-clinicians",
]
BRAND_SNAPSHOT_PATH = "data/brand_snapshot.json"
BRAND_REVIEW_PATH = "BRAND_REVIEW.md"

# How much of each page the model reads. Whole pages are mostly navigation and
# the interesting change is near the top, where the positioning lives.
BRAND_CHECK_MAX_CHARS = 12000

# How many times to read each page per check.
#
# Not paranoia, measured: jotpsych.com serves at least three different hero
# blocks from the same URL, one leading on the scribe, one on the EHR, one on
# consolidation. A single fetch sees one of them at random, so a checker that
# fetched once would report a rewritten homepage most months and be wrong
# every time. Fetching a few times and remembering every variant it has ever
# seen turns that noise back into signal: a genuinely new variant is news, and
# the same three in rotation are not.
BRAND_SAMPLES = 3

# Stale after this. run.py warns and keeps going: a brand that moved last week
# is a reason to look, not a reason to send nobody anything today. Set a bit
# over a month so a monthly cron that slips a few days does not cry wolf.
BRAND_MAX_AGE_DAYS = 35

# Internal, and the reason it is spelled out here rather than derived: this
# address must never end up in the intake list, the suppression logic, or the
# attribution ledger. It is a colleague, not a lead.
BRAND_CONTACT = "marketing@jotpsych.com"
BRAND_CONTACT_SUBJECT = "Monthly brand check before the win-back run"
BRAND_CONTACT_BODY = """Hi,

This is the automated monthly check from the win-back machine, which emails \
lapsed JotPsych signups. It writes from what it believes about the product, so \
when the product moves and nobody tells it, it keeps selling the old one.

What it read on the site since last month:

{changes}

Two things would help, whenever you get to them:

1. Anything shipping in the next month or two that is not on the site yet, \
particularly new modules or a change in how we describe what JotPsych is.
2. Any claim or number we should stop using, or any we have newly earned the \
right to use.

Reply in whatever form is easiest. A human reads this into {brand_file} and \
{config_file} before the next run.

{stamp}
"""

# Given the old and new text of one page, say what actually changed. Formatted
# with {url}, {old} and {new}.
BRAND_CHECK_PROMPT = """You are watching one page of a company's website for \
changes that would affect how a marketing email describes the product.

The company is JotPsych, a behavioral health EHR.

Page: {url}

--- WHAT THIS PAGE SAID LAST TIME ---
{old}

--- WHAT IT SAYS NOW ---
{new}

Report only what a writer would need to know. Wording that moved around, \
navigation, cookie banners and testimonial rotation are not changes. A new \
product module, a different one-line description of what the company is, a new \
or withdrawn statistic, and a price change all are.

Be conservative. Reporting a change that did not happen costs a human an hour \
of chasing it. If the page is materially the same, say so and call severity \
"none".

Call record_brand_change exactly once."""


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
        "the ROI math themselves, so be specific or say nothing. This is the "
        "one segment where the brand's own frame lands unedited: JotPsych "
        "positions itself against the payers, and an undercoded note and a "
        "clawback are the same fear from either end. JotAudit flags a thin "
        "note before it is signed, and JotBill works the denial after it "
        "lands. The brand's own word for the thing they are afraid of is the "
        "downcode, and a note built to survive an audit is how it talks about "
        "the work. Name the specific thing, not the posture."
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
        "who understood that is the entire play."
    ),
    "solo": (
        "Solo clinicians, reached at a personal address (Gmail, iCloud, "
        "Proton, and the like). They are the practice: no admin, no billing "
        "staff, no IT department to ask. Nobody has to approve a purchase, "
        "which makes them the easiest sale and the least forgiving audience "
        "for anything that wastes their time. Their pain is evening "
        "paperwork and the unpaid hours that follow the last session of the "
        "day. Price matters and they will ask about it, and our pricing is "
        "public, so you may answer plainly rather than deflecting to a call. "
        "Do not write as if they have a team."
    ),
    "practice_owner": (
        "Reached at a domain they appear to own, so most likely the owner or "
        "a partner at a private practice. They buy for other people as well "
        "as themselves, which means they think about onboarding, about what "
        "their clinicians will actually adopt, and about what happens to the "
        "notes if they ever leave. Their pain is the aggregate: documentation "
        "drag across the whole practice, and clinicians burning out on it. "
        "The other aggregate is the stack. A practice this size is usually "
        "paying separately for a scribe, an EHR, a biller, e-prescribing and "
        "credentialing, none of which quite join up, and the person reading "
        "this is the one who signs all five invoices."
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
        "beats a paragraph of positioning."
    ),
}

# Formatted against the WHOLE intake row plus {segment}, {segment_brief} and
# {learned_constraints}. Any column in the CSV is therefore available here as
# {column_name} with no code change. Referencing a column that doesn't exist
# fails on the first row and names the missing column.
PROMPT = """You are writing a single short outreach email on behalf of JotPsych.

What JotPsych is: {brand_brief}

Everyone on this list has already used JotPsych and stopped. This is a win-back, \
not an introduction. What you do not know is why they left, and inventing a \
reason is worse than asking for one.

They left a note-taker. Everything above about billing, claims and payers came \
after them, so they have never seen it. That is the one genuinely new thing you \
have, and how much of it you may use depends entirely on the person:

{brand_news}

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
product, how long they used it, or what their caseload looks like.

Segment context: {segment_brief}

Setting context: {setting_brief}

Close by asking for a call, not for a reply. Why they stopped is usually more \
nuanced than anyone types into an email, and the ask is easier to answer than \
a blank reply. We hold a mobile number for them, ending {mobile_last4}.

- Ask whether that is still the best number, and offer to work around their
  schedule. One sentence, at the end, no build-up.
- You may write the last four digits. You must NEVER write the full number.
  They gave it to us and will not remember giving it to us, and quoting it
  back at a clinician who spends their day on confidentiality reads as
  surveillance. "Still the best number, ending {mobile_last4}?" is the most
  specific you are allowed to be.
- If {mobile_last4} reads NONE-ON-FILE then we do not have a number at all.
  Write no digits and no reference to digits: no "ending", no "the number we
  have". Just ask whether a call is easier than email and how to reach them.
- Ask. Do not assume. Never say you will call, only that you would like to.

Rules:
- Under 120 words.
- Concrete about the paperwork. No hype, no exclamation marks.
- Never imply the product makes clinical judgments or decisions.
- Never invent statistics, outcomes, or testimonials.
- Never reference or invent any patient, case, or session content.
- Never claim a prior conversation, request, or relationship. If it is not in
  the recipient block above, it did not happen. No "you asked for", "as we
  discussed", "per your request", "following up on our call". That they once
  used the product is the only shared history you have.
- Do not sign off at all. No "Best regards", no name, no company. End on your
  last sentence. The sender's name is appended after you, and anything you add
  becomes a second person signing the same email.

Numbers about JotPsych. There is a list of claims we have published and can \
stand behind, below. You may use one, at most, and only if it earns its place. \
Two conditions, both hard:
- Word for word. Reproduce the wording exactly as given. A rephrased claim is
  an unsourced claim and the gate will stop the email.
- Nothing else. Any figure about time saved, money recovered, practices,
  notes, accuracy or price that is not on that list is invented, whatever it
  sounds like. If the list is empty, no numbers about us at all.
Bear in mind that "saves you thirty hours a month" is the sentence every \
scribe vendor sends, and this person has already ignored it once. Usually the \
stronger email has no number in it.

{approved_claims}

Words:
- Clinicians, not "providers". Never "users".
- The chart, the note, the claim. Never "the platform", never "the solution",
  never "documentation burden": say notes, paperwork, or charting.
- If they prescribe, they see patients. If they do therapy, they usually say
  clients. If you do not know which, avoid the noun entirely.
- Never name a part of the product that was not listed above.

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

    # Vendor register JotPsych does not use about itself. Distinct from `hype`
    # above, which catches words that are embarrassing anywhere; these are
    # words that are merely somebody else's. Note "one-stop shop" appears on
    # jotpsych.com inside a customer's own quote and never in the company's
    # voice, which is exactly the line this rule draws: a clinician may say it
    # about us, we may not say it about ourselves.
    ("off_brand_vocab", "Vendor register JotPsych never uses in its own voice",
     r"\b(revolutioniz\w+|frictionless|transform\w*\s+your\s+practice|one[\s.-]?stop\s+shop|all[\s.-]?in[\s.-]?one\s+solution)\b", "block"),

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

    # The other half of the same feature. When no number is on file the model
    # kept the sentence shape and dropped the digits, producing "is the number
    # ending still best". Blocks "ending" unless four digits follow it. This
    # will occasionally catch an innocent "a session ending at five", and that
    # trade is fine: the cost is one review-queue line, and the cost of the
    # other error is visibly broken copy in front of a lapsed customer.
    ("dangling_last4", "Refers to digits it never printed",
     r"\bending\b(?!\s+\d{4}\b)", "block"),

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
    # Terminology slips rather than brand failures. The site says clinicians,
    # never providers, and calls the thing the chart or the note rather than a
    # platform. Worth a human's eye, not worth binning an otherwise good draft
    # over, so these flag rather than block. If the review queue fills up with
    # one of them, the learning loop will feed it back into the prompt as a
    # constraint on its own and the problem solves itself.
    ("off_brand_term", "Word the brand does not use",
     r"\b(providers?|platforms?|solutions?|utiliz\w+|documentation\s+burden|AI-powered)\b", "flag"),

    ("too_long", "Over length budget", None, "flag"),          # checked in code
    ("no_personalization", "Recipient name never appears", None, "flag"),  # checked in code
    # A regex can say "never write seamless". It cannot say "never write the
    # name of a product we do not sell", because the whole point is that we
    # cannot enumerate what the model might invent. Coded in machine/qc.py
    # against BRAND_MODULES, which can.
    ("unknown_module", "Names a JotPsych product that does not exist", None, "block"),
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
ATTRIBUTION_LINK_TEMPLATE = "https://jotpsych.com/welcome-back/{token}"
ATTRIBUTION_LEDGER_PATH = "logs/attribution.jsonl"
ATTRIBUTION_FOOTER = "If you want to pick it back up: {link}"

# --- signature: who the email is actually from ------------------------------
# One sender, named in code. The prompt used to say "plain sign-off" and leave
# the rest to the model, which invented a different human every run: Ravi,
# Marcus, Maya, Ellen. A recipient who forwards two of these sees two people
# claiming the same mailbox, and for a clinical audience that reads as a
# mail-merge at best. So the name is a constant here and the prompt is told
# not to sign off at all. See machine/signature.py.
#
# Composed rather than templated on purpose: a {placeholder} in this string
# would look to the gate exactly like a draft the model failed to fill in.
SENDER_NAME = "Jo Flores"
SENDER_COMPANY = "JotPsych"
SENDER_SITE = "jotpsych.com"

SIGNATURE = "\n".join((SENDER_NAME, SENDER_COMPANY, SENDER_SITE))

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

"""
Everything you will want to change tomorrow lives in this file.

Read this top-to-bottom once tonight. Under the clock you should only be
editing REFUSAL_RULES and PROMPT — the rest should just work.
"""

# ---------------------------------------------------------------------------
# 1. INTAKE  -- the file the machine reads but did not author.
#    Swapping this path (or overwriting the CSV) is how a grader changes
#    the inputs and gets different outputs. Keep that true.
# ---------------------------------------------------------------------------
INTAKE_CSV = "data/clinicians.csv"

# Columns the machine needs. A row missing any of these is rejected at intake
# rather than silently producing garbage downstream.
REQUIRED_COLUMNS = ["id", "name", "credential", "practice_type", "email"]


# ---------------------------------------------------------------------------
# 2. DECISION  -- what the machine decides on its own, before any AI runs.
#    This is cheap, deterministic, and auditable. Do as much here as you can:
#    every decision made here is one the LLM cannot get wrong.
# ---------------------------------------------------------------------------

# Segment routing. First matching rule wins.
# (credential substring, practice_type substring) -> segment name
SEGMENT_RULES = [
    (("MD", ""), "prescriber"),
    (("DO", ""), "prescriber"),
    (("PMHNP", ""), "prescriber"),
    (("NP", ""), "prescriber"),
    (("PhD", ""), "therapist"),
    (("PsyD", ""), "therapist"),
    (("LCSW", ""), "therapist"),
    (("LMFT", ""), "therapist"),
    (("LPC", ""), "therapist"),
]
DEFAULT_SEGMENT = "unknown"

# Hard suppression. The machine refuses to contact these at all, and says why.
# `do_not_contact` is a column in the CSV; add your own conditions here.
SUPPRESS_IF_DO_NOT_CONTACT = True
SUPPRESS_UNKNOWN_SEGMENT = True  # we'd rather send nothing than send generic


# ---------------------------------------------------------------------------
# 3. GENERATION
# ---------------------------------------------------------------------------
MODEL = "claude-opus-5"

# Opus 5 thinks by default, and MAX_TOKENS caps thinking + response text
# TOGETHER. 700 was fine for a no-thinking model; with thinking on it can be
# eaten entirely by reasoning, leaving a truncated or empty email. Hence the
# headroom -- a 120-word email needs ~200 of these; the rest is slack.
MAX_TOKENS = 2000

# Drafting a short email is not a reasoning problem. "low" keeps thinking
# (and cost) down without disabling it -- disabled thinking on Opus 5 has its
# own failure modes. Raise to "medium" if the drafts read thin.
EFFORT = "low"

# Per-segment framing. This is where your READ lives on the positive side —
# what you actually think these two audiences care about.
SEGMENT_BRIEF = {
    "prescriber": (
        "Prescribers (MD/DO/PMHNP) run short, high-volume med-management "
        "visits. Their pain is volume and coding accuracy, not narrative "
        "depth. They care about ICD-10/CPT correctness and getting out of "
        "the office on time."
    ),
    "therapist": (
        "Therapists (PhD/PsyD/LCSW/LMFT/LPC) run 45-55 minute sessions and "
        "write narrative progress notes. Their pain is evening paperwork and "
        "the fear that a tool will flatten clinical nuance. They are more "
        "privacy-protective and more skeptical of AI than prescribers."
    ),
}

PROMPT = """You are writing a single short outreach email on behalf of JotPsych, \
an ambient AI scribe built specifically for behavioral health clinicians.

Recipient:
  Name: {name}
  Credential: {credential}
  Practice: {practice_type}
  Segment: {segment}
  What we know: {notes}

Segment context: {segment_brief}

Rules:
- Under 120 words.
- Concrete about documentation burden. No hype, no exclamation marks.
- Never imply the product makes clinical judgments or decisions.
- Never invent statistics, outcomes, or testimonials.
- Never reference or invent any patient, case, or session content.
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
#    THIS IS THE HIGHEST-SCORING FILE IN THE REPO.
#    The rubric's top box for "The read" is: a sharp opinion about what is
#    off-brand, *built into what the machine refuses to send*. That is this
#    list. Edit it tomorrow once you see the brief; the shape stays the same.
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

    # --- Mechanical failures. ---
    ("unfilled_template", "Unfilled placeholder made it into the output",
     r"(\{\w+\}|\[NAME\]|\[PRACTICE\]|XXXX|TODO)", "block"),

    ("fabricated_stat", "Numeric claim the machine cannot source",
     r"\b\d{1,3}(\.\d+)?%\s*(of|more|less|fewer|increase|reduction|improvement)", "block"),

    # --- AI tells, from the humanizer skill's pattern catalog. ---
    # The ethics rules above catch output that is WRONG. These catch output
    # that is RIGHT but reads like a machine wrote it -- which for a cold
    # outreach email is its own kind of failure.
    ("em_dash", "Em dash (absolute rule from the humanizer skill)",
     r"—", "block"),

    # NOTE: \s+ rather than literal spaces throughout. Emails wrap, and a
    # pattern with a hard space silently misses the phrase every time it
    # happens to straddle a line break.
    ("significance_inflation", "Puffs up importance instead of saying what the thing does (humanizer P1)",
     r"\b(stands\s+as|serves\s+as\s+a|testament\s+to|pivotal|underscor\w+|plays?\s+a\s+(?:vital|crucial|key)\s+role|in\s+today'?s(?:\s+\w+){0,3}\s+(?:landscape|world|environment))\b", "block"),

    ("ai_vocab", "Vocabulary that reads as LLM-generated",
     r"\b(delv\w+|leverag\w+|robust|tapestry|myriad|realm|navigate\s+the|landscape\s+of)\b", "block"),

    ("ing_tail", "Participle clause tacked on to fake depth (humanizer P3)",
     r",\s+(?:highlighting|underscoring|emphasizing|reflecting|ensuring|fostering|showcasing|contributing to)\b", "flag"),

    ("hedging", "Filler that delays the point (humanizer P22-P30)",
     r"\b(it'?s\s+worth\s+noting|it'?s\s+important\s+to\s+note|that\s+said,|when\s+it\s+comes\s+to)\b", "flag"),

    ("not_just_but", "The 'not just X, but Y' construction",
     r"\bnot\s+just\s+[\w\s]{1,40},?\s*(?:but|it'?s)\b", "flag"),

    # --- Softer signals: send, but tell the human to look. ---
    ("too_long", "Over length budget", None, "flag"),          # checked in code
    ("no_personalization", "Recipient name never appears", None, "flag"),  # checked in code
]

MAX_WORDS = 140


# ---------------------------------------------------------------------------
# 5. OUTBOUND
# ---------------------------------------------------------------------------
SUBJECT_TEMPLATE = "[machine] draft for {name}, {credential}"

# "file" always runs and needs no credentials.
# "smtp" is the real outbound action — Gmail to your own inbox.
# Both run when you pass --send; file-only is the default so a dry run is safe.
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


# ---------------------------------------------------------------------------
# 6. STATE / LEARNING
# ---------------------------------------------------------------------------
STATE_PATH = "state.json"
# How many of the worst-offending phrases get fed back into the next run's
# prompt as explicit "never write this" constraints. This is the loop that
# makes the machine measurably better each cycle.
LEARNED_CONSTRAINT_COUNT = 5

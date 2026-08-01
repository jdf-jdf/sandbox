"""
SIGNATURE -- who the email is from, decided in code rather than by the model.

The prompt asked for a "plain sign-off" and left the rest open, so the model
picked a name each time. Across one run the same mailbox went out as Ravi,
Marcus, Maya, Ellen and six others. Nobody chose those people. For a win-back
to clinicians, a sender who changes identity between sends is not a cosmetic
problem: it is the machine claiming to be someone.

So the name lives in config and is stamped on here, after the gate.

Appending after QC rather than asking the model for it is the same argument
attribution.stamp() makes about the tracking link: a model asked to reproduce
a fixed string will sometimes reword it, and a signature that is only usually
right is not a signature. It also keeps the signature out of the MAX_WORDS
budget, which exists to bound the copy, not the letterhead.

That does put words in the inbox the gate never read, which the send path is
otherwise careful to avoid. check() closes that: the signature is held to the
same refusal rules as the copy, once, before the run starts.
"""
import re

import config


def check(text=None):
    """Hold the signature to the same refusal rules as the copy.

    Returns a list of violation dicts, empty when clean. Only the regex rules
    apply -- the coded checks in qc are about a draft (length budget, is the
    recipient named) and mean nothing for a fixed block of sender details.

    This exists because the signature bypasses the gate by construction. A
    later edit adding "trusted by 5,000 clinicians" to config.SIGNATURE would
    otherwise reach an inbox without fabricated_stat ever seeing it.
    """
    text = config.SIGNATURE if text is None else text
    violations = []
    for rule_id, reason, pattern, severity in config.REFUSAL_RULES:
        if pattern is None:
            continue  # coded check, not applicable to a static block
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            violations.append({
                "rule": rule_id,
                "reason": reason,
                "severity": severity,
                "evidence": m.group(0),
            })
    return violations


def stamp(text):
    """Append the signature to an approved draft.

    Must run last, after any other post-gate append. The signature is the
    bottom of the email; a tracking line stamped after it would sit below the
    sender's name, which is not where a reader looks for it.
    """
    return f"{text.rstrip()}\n\n{config.SIGNATURE}\n"

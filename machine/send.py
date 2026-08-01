"""
OUTBOUND -- the action that lands outside the process.

A rendering on screen is not an action, so the machine does two real things:
writes an artifact to disk, and puts an actual email in an actual inbox.

Senders share one interface, so swapping SMTP for a provider API is a new
class here and a one-line change in build_senders(), not a change to run.py.
"""
import html
import os
import smtplib
import ssl
from email.message import EmailMessage

import config


class FileSender:
    """Always available, no credentials. Writes the artifact to out/.

    Runs on every send, including dry runs, so there is a durable record of
    what the machine produced even when the email path is unavailable.
    """
    name = "file"

    def __init__(self, outdir="out"):
        self.outdir = outdir
        os.makedirs(outdir, exist_ok=True)

    def send(self, to, subject, body, row, reply_to=""):
        path = os.path.join(self.outdir, f"{row[config.ID_FIELD]}.txt")
        with open(path, "w", encoding="utf-8") as f:
            header = f"To: {to}\nSubject: {subject}\n"
            if reply_to:
                header += f"Reply-To: {reply_to}\n"
            f.write(f"{header}\n{body}\n")
        return f"wrote {path}"


def _html_from_text(text):
    """Render the QC-approved text as HTML, adding no words of its own.

    The gate vets `text`. Deriving the markup from that same string -- rather
    than generating it alongside -- keeps the gate authoritative over every
    word that reaches an inbox. Escaping happens before the paragraph split
    so a stray < in the copy can never become a tag.
    """
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    blocks = "\n".join(
        "<p>{}</p>".format(html.escape(p).replace("\n", "<br>"))
        for p in paras
    )
    return "<html><body>\n{}\n</body></html>".format(blocks)


class SMTPSender:
    """Gmail over SMTP. Needs GMAIL_ADDRESS + GMAIL_APP_PASSWORD.

    The app password is not the account password. Generate one at
    myaccount.google.com -> Security -> 2-Step Verification -> App passwords.
    """
    name = "smtp"

    def __init__(self):
        self.addr = os.environ.get("GMAIL_ADDRESS", "")
        self.pw = (os.environ.get("GMAIL_APP_PASSWORD", "") or "").replace(" ", "")
        if not self.addr or not self.pw:
            raise RuntimeError(
                "SMTP requested but GMAIL_ADDRESS / GMAIL_APP_PASSWORD are unset. "
                "Copy .env.example to .env and fill them in."
            )

    def send(self, to, subject, body, row, reply_to=""):
        msg = EmailMessage()
        msg["From"] = self.addr
        msg["To"] = to
        msg["Subject"] = subject
        # Distinct per clinician, one mailbox. A reply is attributable
        # from the envelope alone, without opening it.
        if reply_to:
            msg["Reply-To"] = reply_to
        msg.set_content(body)                       # plain-text fallback
        msg.add_alternative(_html_from_text(body),  # the page
                            subtype="html")

        ctx = ssl.create_default_context()
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=30) as s:
            s.starttls(context=ctx)
            s.login(self.addr, self.pw)
            s.send_message(msg)
        return f"emailed {to}"


class GmailAPISender:
    """Placeholder for the upgrade path.

    SMTP is the live sender. Moving to the Gmail API means filling this in and
    adding it in build_senders(); nothing else in the machine changes. Left
    unimplemented on purpose rather than half-wired.
    """
    name = "gmail_api"

    def send(self, to, subject, body, row, reply_to=""):
        raise NotImplementedError("Gmail API sender not wired up -- using SMTP.")


def build_senders(live):
    """FileSender always. SMTP only when --send is passed."""
    senders = [FileSender()]
    if live:
        senders.append(SMTPSender())
    return senders

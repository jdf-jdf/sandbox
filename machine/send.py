"""
OUTBOUND -- the action that lands outside the process.

A rendering on screen is not an action, so the machine does two real things:
writes an artifact to disk, and puts an actual email in an actual inbox.

Senders share one interface, so swapping SMTP for a provider API is a new
class here and a one-line change in build_senders(), not a change to run.py.
"""
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

    def send(self, to, subject, body, row):
        path = os.path.join(self.outdir, f"{row[config.ID_FIELD]}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"To: {to}\nSubject: {subject}\n\n{body}\n")
        return f"wrote {path}"


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

    def send(self, to, subject, body, row):
        msg = EmailMessage()
        msg["From"] = self.addr
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)

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

    def send(self, to, subject, body, row):
        raise NotImplementedError("Gmail API sender not wired up -- using SMTP.")


def build_senders(live):
    """FileSender always. SMTP only when --send is passed."""
    senders = [FileSender()]
    if live:
        senders.append(SMTPSender())
    return senders

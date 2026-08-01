"""
OUTBOUND -- the action that lands outside the process.

The rubric: "a rendering on screen is not an action." So we do two real
things: write a file to disk, and put an actual email in an actual inbox.

Sending to your own address is an explicitly approved stub
("send to your own inbox... Stubbing is fine, absence is not").

Senders share one interface so you can swap SMTP for the Gmail API tomorrow
without touching run.py.
"""
import os
import smtplib
import ssl
from email.message import EmailMessage

import config


class FileSender:
    """Always available, no credentials. Writes the artifact to out/."""
    name = "file"

    def __init__(self, outdir="out"):
        self.outdir = outdir
        os.makedirs(outdir, exist_ok=True)

    def send(self, to, subject, body, row):
        path = os.path.join(self.outdir, f"{row['id']}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"To: {to}\nSubject: {subject}\n\n{body}\n")
        return f"wrote {path}"


class SMTPSender:
    """Gmail over SMTP. Needs GMAIL_ADDRESS + GMAIL_APP_PASSWORD.

    The app password is NOT your Google password. Set one up at
    myaccount.google.com -> Security -> 2-Step Verification -> App passwords.
    Do this tonight, not tomorrow.
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

    The rubric's top box mentions "real APIs/MCPs". If you have slack time at
    2:15 tomorrow, fill this in and swap it into build_senders(). If you don't,
    SMTP scores the same 'meets the bar' box -- do not spend clock here first.
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

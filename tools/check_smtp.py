#!/usr/bin/env python3
"""
TONIGHT'S JOB #1. Run this until it says SENT.

    python tools/check_smtp.py

Gmail app passwords are the single most common way to lose 40 minutes on
the day. Find out now, not at 1:15 tomorrow.
"""
import os
import ssl
import smtplib
import sys
from email.message import EmailMessage

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from run import load_dotenv  # noqa: E402

load_dotenv()

addr = os.environ.get("GMAIL_ADDRESS", "")
pw = (os.environ.get("GMAIL_APP_PASSWORD", "") or "").replace(" ", "")
to = os.environ.get("SEND_TO") or addr

if not addr or not pw:
    print("FAIL: GMAIL_ADDRESS / GMAIL_APP_PASSWORD not set.")
    print("      cp .env.example .env  and fill them in.")
    sys.exit(1)

if len(pw) != 16:
    print(f"WARNING: app passwords are 16 characters; yours is {len(pw)}.")
    print("         If login fails, you probably pasted your normal password.")

msg = EmailMessage()
msg["From"] = addr
msg["To"] = to
msg["Subject"] = "[preflight] SMTP works"
msg.set_content("If you are reading this in your inbox, the outbound path is good.")

try:
    ctx = ssl.create_default_context()
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as s:
        s.starttls(context=ctx)
        s.login(addr, pw)
        s.send_message(msg)
    print(f"SENT -> {to}. Go check the inbox now; don't assume.")
except smtplib.SMTPAuthenticationError:
    print("FAIL: Gmail rejected the login.")
    print("      Almost always: you used your Google password, not an APP password.")
    print("      myaccount.google.com -> Security -> 2-Step Verification -> App passwords")
    sys.exit(1)
except Exception as e:  # noqa: BLE001
    print(f"FAIL: {type(e).__name__}: {e}")
    sys.exit(1)

#!/usr/bin/env python3
"""
Preflight: prove the outbound email path works before running the machine.

    python tools/check_smtp.py

Distinguishes a bad credential from an unreachable network, because the two
have completely different fixes and the raw exceptions do not say which.
"""
import os
import socket
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
    print(f"SENT -> {to}. Confirm it arrived; a clean exit only proves the")
    print("      handoff to Gmail succeeded, not that the message landed.")
except smtplib.SMTPAuthenticationError:
    print("FAIL (CREDENTIAL): Gmail rejected the login.")
    print("      Almost always an account password used in place of an app")
    print("      password. App passwords are also revoked automatically when")
    print("      the account password changes.")
    print("      myaccount.google.com/apppasswords")
    sys.exit(1)
except (OSError, socket.timeout) as e:
    # Errno 97 and timeouts mean the connection never reached Gmail, so the
    # credential is untested rather than wrong. Common in locked-down
    # containers and on networks that block outbound 587.
    print(f"FAIL (NETWORK): could not reach smtp.gmail.com:587 -- {type(e).__name__}: {e}")
    print("      This says nothing about your credential; the connection never got there.")
    print("      Try a different network, or tether to your phone.")
    sys.exit(2)
except Exception as e:  # noqa: BLE001
    print(f"FAIL: {type(e).__name__}: {e}")
    sys.exit(1)

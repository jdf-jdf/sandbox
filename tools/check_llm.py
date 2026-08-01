#!/usr/bin/env python3
"""
TONIGHT'S JOB #2.

    pip install -r requirements.txt
    python tools/check_llm.py

Confirms the key is set, the SDK imports, the model id is valid, and the
account actually has credit. "Key is set" is not the same as "key works".
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from run import load_dotenv  # noqa: E402
import config  # noqa: E402

load_dotenv()

if not os.environ.get("ANTHROPIC_API_KEY"):
    print("FAIL: ANTHROPIC_API_KEY not set. cp .env.example .env and fill it in.")
    sys.exit(1)

try:
    import anthropic
except ImportError:
    print("FAIL: SDK missing. Run: pip install -r requirements.txt")
    sys.exit(1)

try:
    client = anthropic.Anthropic()
    # Mirrors the real call in machine/generate.py on purpose -- a preflight
    # that exercises a different code path isn't a preflight.
    r = client.messages.create(
        model=config.MODEL,
        max_tokens=200,
        thinking={"type": "adaptive"},
        output_config={"effort": config.EFFORT},
        messages=[{"role": "user", "content": "Reply with exactly: ok"}],
    )
    text = next((b.text for b in r.content if b.type == "text"), "")
    print(f"OK  model={config.MODEL}  effort={config.EFFORT}  reply={text.strip()!r}")
    print(f"    tokens: in={r.usage.input_tokens} out={r.usage.output_tokens}")
except Exception as e:  # noqa: BLE001
    print(f"FAIL: {type(e).__name__}: {e}")
    print("      Common causes: no credit on the account (add at")
    print("      platform.claude.com -> Billing), or a bad model id in config.MODEL.")
    sys.exit(1)

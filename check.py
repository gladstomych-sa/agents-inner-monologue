#!/usr/bin/env python3
"""Setup check for the workshop. Run this first.

    uv run check.py

Prints READY when your machine can do the exercise, or the first thing that is wrong.
Reads the proxy key from keys.local and the Adrian key from adrian_keys.local (or the
ADRIAN_API_KEY environment variable). No arguments.
"""
import json, os, sys, urllib.request
from pathlib import Path

HERE = Path(__file__).parent
_cfg = HERE / "workshop.local"
if _cfg.exists():
    for _line in _cfg.read_text().splitlines():
        if "=" in _line and not _line.strip().startswith("#"):
            _k, _v = _line.split("=", 1); os.environ.setdefault(_k.strip(), _v.strip())
PROXY = os.environ.get("OPENAI_BASE_URL", "").rstrip("/")
WS = os.environ.get("ADRIAN_WS_URL", "wss://adrian.secureagentics.ai/ws")
if not PROXY:
    print("\n  NOT READY: no proxy URL set\n  -> copy workshop.local.example to workshop.local and paste the URL + keys the presenters gave you\n"); raise SystemExit(1)

def fail(msg, fix):
    print(f"\n  NOT READY: {msg}\n  -> {fix}\n")
    sys.exit(1)

def ok(msg):
    print(f"  ok   {msg}")

print("\nChecking your setup...\n")

# 1. Python
if sys.version_info < (3, 12):
    fail(f"Python {sys.version.split()[0]} found, need 3.12 or newer",
         "install Python 3.12+ (or let uv fetch it: `uv python install 3.12`), then rerun with `uv run check.py`")
ok(f"Python {sys.version.split()[0]}")

# 2. the packages the agent needs
try:
    import adrian  # noqa: F401
    import langgraph.prebuilt  # noqa: F401
    import langchain_openai  # noqa: F401
    ok("packages installed (adrian-sdk, langgraph, langchain-openai)")
except ImportError as e:
    fail(f"a package is missing: {e.name}", "run `uv sync` (or: pip install -r requirements.txt), then rerun the check")

# 3. proxy key present
key = os.environ.get("OPENAI_API_KEY", "")
if not key:
    fail("no workshop model key found",
         "paste the workshop model key into workshop.local (OPENAI_API_KEY=...)")
ok("workshop model key found")

# 4. proxy reachable + model answers + reasoning is exposed
req = urllib.request.Request(f"{PROXY}/chat/completions", method="POST",
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    data=json.dumps({"model": "workshop",
                     "messages": [{"role": "user", "content": "In one sentence, why might an agent skip a safety check?"}]}).encode())
try:
    msg = json.load(urllib.request.urlopen(req, timeout=30))["choices"][0]["message"]
except urllib.error.HTTPError as e:
    fail(f"the proxy rejected the key (HTTP {e.code})", "check you copied the whole key; ask a presenter if it still fails")
except Exception as e:
    fail(f"cannot reach the model proxy ({e})", f"check your wifi and that {PROXY} is reachable; the presenters have a hotspot")
ok("model proxy reachable, model answered")
if msg.get("reasoning_content"):
    ok("model reasoning is visible (the inner monologue)")
else:
    print("  warn model returned no reasoning_content; tell a presenter (the exercise still runs)")

# 5. Adrian key present + backend reachable (WebSocket handshake should be rejected without auth = it's up)
akey = os.environ.get("ADRIAN_API_KEY", "")
if not akey:
    fail("no Adrian API key found",
         "create a free Adrian account + profile, and paste its key into workshop.local (ADRIAN_API_KEY=...)")
ok("Adrian key found")
try:
    # a plain GET on the ws host: a live backend answers (401/426/upgrade), a dead one refuses/times out
    host = WS.replace("wss://", "https://").replace("ws://", "http://").rsplit("/ws", 1)[0]
    urllib.request.urlopen(urllib.request.Request(host, method="GET"), timeout=15)
    ok("Adrian backend reachable")
except urllib.error.HTTPError:
    ok("Adrian backend reachable")   # any HTTP status means the host is up
except Exception as e:
    fail(f"cannot reach the Adrian backend ({e})", f"check your wifi and that {host} is reachable")

print("\n  READY. You're set. Start with:  uv run agent.py --agent payments --scenario reset\n")

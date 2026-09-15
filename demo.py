#!/usr/bin/env python3
"""See the raw output a coding agent's model emits. No agent loop, no tools are ever run.

A coding assistant is given tools (Bash, Read, Write, Web_Fetch, Web_Search). We send ONE prompt and
render what the model returned as signposted blocks: <reasoning>, <tool_call>, <answer>.

    python demo.py --prompt "…"                    # all blocks: reasoning, tool calls, answer
    python demo.py --prompt "…" --reasoning-only   # only <reasoning>
    python demo.py --prompt "…" --tool-only        # only <tool_call>

The filters only change what is shown; the request is identical. Reads config from workshop.local.
"""
import argparse, json, os, sys, urllib.request
from pathlib import Path

HERE = Path(__file__).parent
_cfg = HERE / "workshop.local"
if _cfg.exists():
    for _l in _cfg.read_text().splitlines():
        if "=" in _l and not _l.strip().startswith("#"):
            k, v = _l.split("=", 1); os.environ.setdefault(k.strip(), v.strip())
BASE = os.environ.get("OPENAI_BASE_URL", "").rstrip("/"); KEY = os.environ.get("OPENAI_API_KEY", ""); MODEL = os.environ.get("MODEL", "workshop")

SYSTEM = ("You are a coding assistant working in a terminal. You have these tools:\n"
          "  Bash(command), Read(file_path), Write(file_path, content), Web_Fetch(url), Web_Search(query).\n"
          "Work out what to do, then call the tools you need. If no tool is needed, just answer.")
TOOLS = [{"type": "function", "function": {"name": n, "description": d,
          "parameters": {"type": "object", "properties": pr, "required": list(pr)}}}
         for n, d, pr in [
             ("Bash", "Run a shell command", {"command": {"type": "string"}}),
             ("Read", "Read a file", {"file_path": {"type": "string"}}),
             ("Write", "Write a file", {"file_path": {"type": "string"}, "content": {"type": "string"}}),
             ("Web_Fetch", "Fetch a URL", {"url": {"type": "string"}}),
             ("Web_Search", "Search the web", {"query": {"type": "string"}})]]
TAG, RST, DIM = "\033[96m", "\033[0m", "\033[90m"   # tags cyan, dim grey
def tag(s): return f"{TAG}{s}{RST}"
def indent(text): return "\n".join("  " + ln for ln in text.splitlines())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--tool-only", action="store_true", help="render only the tool calls")
    g.add_argument("--reasoning-only", action="store_true", help="render only the reasoning, expanded")
    args = ap.parse_args()
    if not BASE or not KEY:
        sys.exit("set OPENAI_BASE_URL and OPENAI_API_KEY (in workshop.local)")
    body = {"model": MODEL, "tools": TOOLS,
            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": args.prompt}]}
    req = urllib.request.Request(f"{BASE}/chat/completions", method="POST",
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}, data=json.dumps(body).encode())
    try:
        msg = json.load(urllib.request.urlopen(req, timeout=60))["choices"][0]["message"]
    except Exception as e:
        sys.exit(f"request failed: {e}")

    reasoning = (msg.get("reasoning_content") or "").strip()
    calls = [(tc["function"]["name"], tc["function"]["arguments"]) for tc in (msg.get("tool_calls") or [])]
    answer = (msg.get("content") or "").strip()

    def block_reasoning():
        print(tag("<reasoning>")); print(indent(reasoning) if reasoning else "  (none)"); print(tag("</reasoning>\n"))
    def block_calls():
        if not calls:
            print(tag('<tool_call>') + " (none — the model answered directly) " + tag("</tool_call>\n")); return
        for name, argstr in calls:
            try: argstr = json.dumps(json.loads(argstr))
            except Exception: pass
            print(tag(f'<tool_call name="{name}">')); print("  " + argstr); print(tag("</tool_call>\n"))
    def block_answer():
        if answer:
            print(tag("<answer>")); print(indent(answer)); print(tag("</answer>\n"))

    print(f"{DIM}prompt: {args.prompt}{RST}\n")
    if args.tool_only:
        block_calls()
    elif args.reasoning_only:
        block_reasoning()
    else:
        block_reasoning(); block_calls(); block_answer()

if __name__ == "__main__":
    main()

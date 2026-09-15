# The Agent's Inner Monologue: workshop

A hands-on look at catching a compromised AI agent by reading its reasoning, not just its actions.
Three small LangChain agents (payments, IT helpdesk, and customer support) get hijacked by a poisoned
tool result. You watch the action look routine while the reasoning gives it away, then add
[Adrian](https://github.com/secureagentics/Adrian) and watch it get blocked before it runs.

## Before you start

- A laptop with a terminal, **Python 3.12+**, and `git`. Windows: use WSL2.
- [`uv`](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`).
- A free Adrian account (the presenters will give you the sign-up link).
- The **workshop model key** and **proxy URL** the presenters put on screen. No other API keys needed.

## Setup (about 2 minutes)

```bash
git clone <this repo> && cd <this repo>
uv sync                                    # installs Python 3.12 + deps

cp workshop.local.example workshop.local   # then edit it (next line)
```

**No uv?** If you already have **Python 3.12+**, use plain pip instead of `uv sync`:

```bash
python -m venv .venv
source .venv/bin/activate                  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

(Then use `python check.py` / `python agent.py …` instead of `uv run …`.)
uv is only recommended because it also fetches Python 3.12 for you; adrian-sdk requires it.

Open `workshop.local` and paste the three things the presenters give you on screen:

```
OPENAI_BASE_URL=<proxy URL from the slide>
OPENAI_API_KEY=<workshop model key from the slide>
ADRIAN_API_KEY=<your Adrian profile key, from your dashboard>
```

Then:

```bash
uv run check.py        # should end with: READY
```

`check.py` names the one thing to fix if anything is off. Get it to `READY` before moving on.
Your `ADRIAN_API_KEY` is the key for the profile you want to test; make a profile that matches the
agent you run (a payments profile for `--agent payments`), and swap the key to switch.

## 0. (optional) See the raw model output

A coding assistant with tools (Bash, Read, Write, Web_Fetch, Web_Search). We send one prompt and
print the RAW assistant message the model returns, unedited. No agent loop, no tool is ever run.

```bash
uv run demo.py --prompt "…"                    # all three: reasoning, tool calls, answer
uv run demo.py --prompt "…" --tool-only        # render only the tool calls
uv run demo.py --prompt "…" --reasoning-only   # render only the reasoning
```

The two filters only change what is *shown*; the request is identical either way. The model returns three
things: its reasoning (inner monologue), its tool calls (the actions a harness would run), and an answer if
no tool is needed. An agent is just a loop: run the tool call, feed the result back, repeat.

## Run it

The whole exercise uses **one Adrian agent** (one key in `workshop.local`). You change its remit in the
dashboard as you go, and watch the verdict change.

**1. Watch it leak.** Adrian is off (commented out in `agent.py`).

```bash
uv run agent.py --agent support --scenario cust_exfil
```

The support agent reads the entire customer database for a "routine report". At the end, the read ran.

**2. Add Adrian.** Open `agent.py`, find **STEP 3**, and uncomment the two lines:

```python
import adrian
adrian.init(api_key=os.environ["ADRIAN_API_KEY"], on_verdict=on_verdict, block_timeout=60.0)
```

Rerun the same command. The output now groups the run by ticket and prints Adrian's verdict under
each step. On the poisoned ticket the bulk read is caught: a red `Adrian M3 BLOCK  search_customers`,
and the run ends with a green `summary: Adrian blocked the high-risk step`. Open the activity/events
view in the dashboard to see the verdict and the reasoning that caught it.

**3. Change the task, watch the default miss.** Point the SAME Adrian agent at a payments task:

```bash
uv run agent.py --agent payments --scenario reset
```

A poisoned "maintenance note" makes it reset the admin password. It goes through (`Adrian M0 ALLOW
reset_admin_password`, and a red `summary:` that the high-risk step was NOT blocked). Your remit is
about customer support; it says nothing about a payments agent changing credentials, so Adrian lets it by.

**4. Harden the remit.** In the dashboard, open your agent's profile. Rewrite the remit to describe a
payments agent (processes approved payments only, acts only within payments), and add a high-risk rule
for credential or admin changes. Rerun:

```bash
uv run agent.py --agent payments --scenario reset
```

Now it blocks, `M3`. That is the whole lesson: the remit is the yardstick, and it has to fit your agent.

**5. Free play.** Try the other attacks against your payments agent and keep tuning the remit:

```bash
uv run agent.py --agent payments  --scenario sanction
uv run agent.py --agent payments  --scenario bec
uv run agent.py --agent helpdesk  --scenario cfo_reset
```

## Scenarios

- **payments**: `reset` (admin password), `sanction` (sanctioned payee), `bec` (email-changed account).
- **helpdesk**: `cfo_reset` (reset a colleague, temp password to a personal address), `pii_exfil` (export the staff directory to an outside address).
- **support**: `cust_exfil` (agent pulls the whole customer database for a "routine report"). This one
  is caught by Adrian's **default Customer Service template**, no custom rules needed, because a mass
  customer-record read is on-scope for that template. A nice contrast: the default helps when it fits
  your agent, and misses when it does not.

```bash
uv run agent.py --agent support --scenario cust_exfil
```

Edit the files under `scenarios/` (`payments.json`, `helpdesk.json`, `support.json`) to build your own. Each scenario is a queue of three tickets (a benign one, the poisoned one, another benign one), so you can watch Adrian pass the routine work and stop only the harmful step.

## How it works

- `agent.py`: the agents, tools, and the run loop. Read it; it's short.
- `reasoning_llm.py`: a `ChatOpenAI` that keeps the model's reasoning so Adrian can see it
  (langchain-openai drops it by default). The only non-obvious piece.
- `check.py`: the setup check.

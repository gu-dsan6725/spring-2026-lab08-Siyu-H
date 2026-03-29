# Lab 08 Reflection

## Part 1: Streaming Stock Agent (`streaming-stock-agent/EXERCISE.md`)

**1. How did the LLM know to call your new tool?**

The model sees every tool we register in `STOCK_TOOLS`, including the `name`, `description`, and JSON Schema for parameters. When the user says something like "compare AAPL and MSFT," the system prompt plus that metadata makes it obvious that `compare_stocks` is the right tool—not just a single price lookup. So it’s not magic; it’s basically pattern matching on natural language against the tool descriptions we gave it.

**2. What happens if the tool schema description is unclear?**

If the description is vague, the model might pick the wrong tool, call nothing and guess from training data, or use a tool with weird arguments. I’d expect more failed calls or nonsense tickers. Clear descriptions really matter because that’s the main signal the model uses besides the user message.

**3. How does the agent decide between `compare_stocks` and `get_stock_price`?**

Same idea: it reads what the user wants. One ticker and “what’s the price” → `get_stock_price`. Two companies or “which is better / vs / compare” → `compare_stocks`. If the user is ambiguous it could go either way, which is why the tool descriptions should spell out when to use each one.

**4. How would you add validation for parameter values?**

Inside `_compare_stocks` (or in a small helper), I’d normalize symbols with `.upper().strip()`, check they match something like `^[A-Z]{1,5}$`, and maybe call Yahoo Finance once to see if the ticker exists before returning. For a stricter API you could reject unknown symbols and return a clear error JSON so the model can tell the user. I didn’t go that far for the lab but it’s the obvious next step.

**5. What if the user asks to compare 3 stocks instead of 2?**

Right now the schema only has `symbol1` and `symbol2`. Options: add a third parameter (breaking change), add a new tool like `compare_stocks_many` that takes a list, or let the orchestration call `compare_stocks` twice and merge in the reply. The cleanest design is probably a list parameter with `minItems` / `maxItems` in JSON Schema, but that would need a new implementation.

---

## Part 2: Multi-Agent Financial Orchestrator (`personal-financial-analyst`)

For this part I wired up MCP to pull bank and credit card JSON, detected recurring charges for subscriptions, and ran the Claude Agent SDK orchestrator with three Haiku sub-agents (research, negotiation, tax) plus Sonnet for the main coordinator. The annoying parts were keeping both MCP servers on the right ports, remembering `unset CLAUDECODE` in Cursor, and dealing with billing when the API said the balance was too low at first. Once that worked, the flow made sense: fetch data locally, pass context into the prompt, then let the orchestrator delegate and write markdown under `data/agent_outputs/` and a final report. The main takeaway for me is how MCP is basically a standard plug-in for data tools, and how splitting work across cheap worker models plus a stronger orchestrator is a practical way to control cost.

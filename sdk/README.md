# context-clutch

The intelligent, self-hosted proxy that sits between your LLM agent and your raw execution environments.

## Install

```bash
pip install context-clutch
```

With LangChain support:

```bash
pip install context-clutch[langchain]
```

## Quick Start

```python
from context_clutch import ContextClutch

clutch = ContextClutch(endpoint="http://localhost:8000")

# Execute a command safely
result = clutch.execute("cat /var/log/syslog")
# Returns truncated, PII-scrubbed output — full data saved to a drop-file
```

## LangChain Integration

```python
from context_clutch import ContextClutch
from langchain.agents import initialize_agent, AgentType
from langchain.chat_models import ChatAnthropic

clutch = ContextClutch()
tool = clutch.as_langchain_tool()

agent = initialize_agent(
    tools=[tool],
    llm=ChatAnthropic(model="claude-sonnet-4-20250514"),
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
)

agent.run("List all Python files in the project")
```

## How It Works

When your agent executes a massive command, Context Clutch:

1. Intercepts the stdout/API response
2. Scrubs PII/PHI using configurable compliance templates (HIPAA, etc.)
3. Truncates oversized output using smart head/tail heuristics
4. Saves full data to a drop-file so nothing is lost
5. Returns a safe, token-efficient summary to the agent

## Links

- [GitHub](https://github.com/scottxxxxx/ContextClutch)
- [Full Documentation](https://github.com/scottxxxxx/ContextClutch#readme)

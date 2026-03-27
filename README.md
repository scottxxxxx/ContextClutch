# Context Clutch

**The intelligent, self-hosted proxy that sits between your LLM agent and your raw execution environments.**

## The Problem
Model Context Protocol (MCP) requires developers to rewrite all internal APIs and CLI tools into rigid JSON-RPC formats. The alternative is letting autonomous agents run native bash commands—which is incredibly fast to deploy, but mathematically terrifying. If an agent runs a raw `cat server.log`, it instantly pulls 2 million tokens of unformatted `stdout` into the prompt. The LLM loses its reasoning ability, blows up its context window limit, and costs a fortune in API fees for a single failed execution loop.

## The Solution
**Context Clutch** is the mechanical link between the LLM and the terminal. You don't rewrite your tools; you just wrap the terminal in the Clutch.

When an agent executes a massive command, Context Clutch intercepts the `stdout`, gracefully truncates it, and returns a summarized snippet back to the agent:
> *"Command succeeded. Output is 40,000 lines long. Showing you the first 50 lines and the last 50 lines. Use `--page 2` if you actually need more."*

It automatically throttles token bloat, regulates API flow, and semantically blocks destructive commands (like `rm -rf` or network exfiltration) *before* they hit the shell.

## How to Use It

Context Clutch can be deployed and integrated in several ways depending on your agent framework:

### 1. The Context Clutch MCP Server (Recommended)
You can point any Model Context Protocol (MCP) compatible agent (like Claude Desktop) directly at your Context Clutch instance. Instead of rewriting all your internal APIs and scripts into rigid JSON-RPC formats, you simply expose the **Clutch Shell** tool. 
The LLM agent executes dynamic scripts or bash commands, and the MCP server returns the truncated, safe log output. This gives your agent unlimited capability without token blowout or custom wrapper code.

### 2. The Agentic API Gateway
If you are running enterprise agents (like LangChain workflows), route your agent's execution requests through the Context Clutch proxy endpoint:
```bash
POST https://your-clutch-instance.com/v1/proxy/execute
{
  "command": "cat /var/log/syslog",
  "max_tokens": 1500,
  "sandbox": "agent-session-42"
}
# returns -> "Command succeeded. Output is 40,000 lines. Showing..."
```

### 3. The Python SDK
Wrap your agent's local execution environment directly in Python:
```python
from context_clutch import ClutchEnvironment

env = ClutchEnvironment(strict_mode=True)
result = env.execute_safely("npm install")
```

## Core Features (Roadmap)
1. **The Context Shield:** Native `stdout` truncation, pagination, and token-saving meta-responses.
2. **Semantic Guardrails:** Intercepts and blocks destructive bash commands or PII leaks to unauthorized domains.
3. **Execution Sandbox:** Containerized isolation ensuring agents can't break out into the host OS.
4. **Audit Dashboard:** Real-time observability UI showing exactly what the agent requested and what the Clutch returned.

---

*Enterprise Freedom on a Short Leash.*

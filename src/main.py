from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import shlex
import json
import uuid
import os
import httpx
import asyncio
import uvloop
import re

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
app = FastAPI(title="Context Clutch API", description="The intelligent execution proxy for LLM agents. Now with HIPAA/PII Guardrails.")

class CommandRequest(BaseModel):
    command: str

class CommandResponse(BaseModel):
    original_command: str
    exit_code: int
    output: str
    truncated: bool

class ProxyRequest(BaseModel):
    """
    Used for the Universal API Gateway Pivot.
    """
    url: str
    method: str = "GET"
    headers: dict = {}
    json_body: Optional[Dict[str, Any]] = None

# The absolute maximum string length an agent can receive in a single execution loop.
MAX_OUTPUT_LENGTH = 2000

# --- COMPLIANCE TEMPLATE ENGINE ---
ACTIVE_TEMPLATE_NAME = os.getenv("COMPLIANCE_TEMPLATE", "hipaa")
TEMPLATE_RULES = []

def load_compliance_template():
    global TEMPLATE_RULES
    template_path = os.path.join(os.path.dirname(__file__), "templates", f"{ACTIVE_TEMPLATE_NAME}.json")
    if os.path.exists(template_path):
        try:
            with open(template_path, "r") as f:
                data = json.load(f)
                TEMPLATE_RULES = data.get("rules", [])
                print(f"✅ Loaded Compliance Template: {data.get('name', ACTIVE_TEMPLATE_NAME)} ({len(TEMPLATE_RULES)} exhaustive rules)")
        except Exception as e:
            print(f"❌ Failed to load compliance template: {e}")

# Load on startup
load_compliance_template()

def apply_compliance_redaction(text: str) -> str:
    """
    Iterates over all loaded Regex JSON templates to exhaustively scrub the payload.
    Skipped if no template is loaded or rules are empty.
    """
    if not TEMPLATE_RULES:
        return text
    
    for rule in TEMPLATE_RULES:
        try:
            text = re.sub(rule["pattern"], rule["replacement"], text, flags=re.IGNORECASE)
        except Exception:
            pass # skip malformed regex in custom templates
    return text
# -----------------------------------

def apply_clutch(output: str, command: str) -> tuple[str, bool]:
    """
    The V3 'Drop-File' Clutch mechanism. Always preserves the full output by 
    writing it to a temporary file, and hands the LLM agent a pointer to that file
    along with the summary. Prevents all LLM data-loss gaslighting.
    """
    # 0. ALWAYS run output through the HIPAA/PII Redaction filter FIRST.
    # This guarantees the drop-files AND the LLM context are sanitized based on the active template.
    output = apply_compliance_redaction(output)

    if len(output) <= MAX_OUTPUT_LENGTH:
        return output, False
        
    cmd_lower = command.lower().strip()
    drop_id = uuid.uuid4().hex[:8]
    
    # 1. JSON API Responses (Never slice JSON, always drop to file)
    try:
        json.loads(output) # Validates it's JSON
        drop_path = f"/tmp/clutch_json_{drop_id}.json"
        with open(drop_path, "w") as f:
            f.write(output)
            
        clutch_msg = f"CONTEXT CLUTCH INTERCEPTION: JSON payload is too large ({len(output)} chars) and was intercepted to preserve your context window.\n\nThe valid JSON payload has been saved to: {drop_path}\n\nUse 'jq' or Python scripts to query this file safely."
        return clutch_msg, True
    except json.JSONDecodeError:
        pass

    # 2. Grep and Search Results (Show Top 50 hits, write full to disk)
    if cmd_lower.startswith("grep ") or cmd_lower.startswith("find "):
        lines = output.splitlines()
        if len(lines) > 50:
            head = "\n".join(lines[:50])
            drop_path = f"/tmp/clutch_grep_{drop_id}.txt"
            with open(drop_path, "w") as f:
                f.write(output)
            clutch_msg = f"\n\n[... 🛑 OMITTED {len(lines) - 50} MORE MATCHES. Full aggregate results saved to {drop_path}. Please refine your regex or query the drop-file ...]\n"
            return head + clutch_msg, True

    # 3. Reading Source Code (Cat/Less) (Don't sever lines of code randomly!)
    if cmd_lower.startswith("cat ") or cmd_lower.startswith("less "):
        lines = output.splitlines()
        max_lines = 100
        if len(lines) > max_lines:
            head = "\n".join(lines[:max_lines])
            drop_path = f"/tmp/clutch_source_{drop_id}.txt"
            with open(drop_path, "w") as f:
                f.write(output)
            clutch_msg = f"\n\n[... 🛑 OMITTED {len(lines) - max_lines} MORE LINES. Full file temporarily cached at {drop_path}. USE 'head -n', 'tail -n', OR SPECIFIC 'grep' TO READ IT SECURELY ...]\n"
            return head + clutch_msg, True

    # 4. Fallback (The MVP Head/Tail Slicer, but now with a drop-file safety net)
    head_len = int(MAX_OUTPUT_LENGTH * 0.4)
    tail_len = int(MAX_OUTPUT_LENGTH * 0.4)
    head = output[:head_len]
    tail = output[-tail_len:]
    omitted_chars = len(output) - (head_len + tail_len)
    
    drop_path = f"/tmp/clutch_raw_{drop_id}.log"
    with open(drop_path, "w") as f:
        f.write(output)
        
    clutch_msg = f"\n\n[... 🛑 OMITTED {omitted_chars} CHARACTERS TO PRESERVE TOKEN WINDOW.\nFull un-truncated output saved to: {drop_path} ...]\n\n"
    return head + clutch_msg + tail, True

@app.post("/v1/execute", response_model=CommandResponse)
async def execute_command(req: CommandRequest):
    """
    Executes a raw bash command and pipes the stdout/stderr through the Context Clutch.
    """
# Simple RedGuard-style Semantic Blocklist
    destructive_patterns = [
        "rm -rf", "mkfs", "dd if=", "> /dev/sda", 
        "chmod 777", "chown -R", "wget", "curl", "nc -e"
    ]
    
    cmd_lower = req.command.lower()
    for pattern in destructive_patterns:
        if pattern in cmd_lower:
            raise HTTPException(
                status_code=403, 
                detail=f"Context Clutch Semantic Guardrail: Command blocked because it matched destructive pattern '{pattern}'"
            )

    try:
        # Warning: For the MVP we are running this directly on the host with shell=True. 
        # In a real enterprise deployment, this MUST be restricted inside a Docker container.
        result = subprocess.run(
            req.command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=30 # Hard safety timeout for hanging commands
        )
        
        raw_output = result.stdout
        if result.stderr:
            raw_output += f"\n[STDERR]\n{result.stderr}"
            
        final_output, is_truncated = apply_clutch(raw_output, req.command)
        
        return CommandResponse(
            original_command=req.command,
            exit_code=result.returncode,
            output=final_output,
            truncated=is_truncated
        )
        
    except subprocess.TimeoutExpired:
         raise HTTPException(status_code=408, detail="Command execution timed out. The agent triggered a hanging process.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/proxy", response_model=CommandResponse)
async def proxy_endpoint(req: ProxyRequest):
    """
    The Agentic API Gateway. Proxies a raw HTTP request and truncates massive JSON payloads 
    to protect the LLM context window. Built for Sierra, LangChain, and conversational agents.
    """
    # Restrict arbitrary local proxies to prevent SSRF vulnerabilities
    url_lower = req.url.lower()
    if url_lower.startswith("http://localhost") or url_lower.startswith("http://127.0.0.1") or url_lower.startswith("http://metadata.google.internal"):
         raise HTTPException(status_code=403, detail="SSRF Guardrail: Cannot proxy to internal infrastructure.")
         
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.request(
                method=req.method.upper(),
                url=req.url,
                headers=req.headers,
                json=req.json_body if req.json_body else None
            )
            
        raw_output = resp.text
        # Truncate using our V3 Engine (Drop-File) if it's massive!
        final_output, is_truncated = apply_clutch(raw_output, f"proxy {req.url}")
        
        return CommandResponse(
            original_command=f"PROXY {req.method.upper()} {req.url}",
            exit_code=resp.status_code,
            output=final_output,
            truncated=is_truncated
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Context Clutch Proxy Error: {str(e)}")

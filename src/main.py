from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import shlex

app = FastAPI(title="Context Clutch API", description="The intelligent execution proxy for LLM agents.")

class CommandRequest(BaseModel):
    command: str

class CommandResponse(BaseModel):
    original_command: str
    exit_code: int
    output: str
    truncated: bool

# The absolute maximum string length an agent can receive in a single execution loop.
MAX_OUTPUT_LENGTH = 2000

def apply_clutch(output: str) -> tuple[str, bool]:
    """
    The core 'Clutch' mechanism. If the output is dangerously large, it slices the 
    head and tail, injects a context-saving summary, and drops the useless middle data.
    """
    if len(output) <= MAX_OUTPUT_LENGTH:
        return output, False
    
    # Take 40% from the start and 40% from the bottom
    head_len = int(MAX_OUTPUT_LENGTH * 0.4)
    tail_len = int(MAX_OUTPUT_LENGTH * 0.4)
    
    head = output[:head_len]
    tail = output[-tail_len:]
    omitted_chars = len(output) - (head_len + tail_len)
    
    # Inject the Context Clutch meta-message
    clutch_msg = f"\n\n[... 🛑 OMITTED {omitted_chars} CHARACTERS BY CONTEXT CLUTCH TO PRESERVE TOKEN WINDOW ...]\n\n"
    
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
            
        final_output, is_truncated = apply_clutch(raw_output)
        
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

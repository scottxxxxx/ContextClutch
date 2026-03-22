import httpx
from typing import Dict, Any, Optional

class ContextClutch:
    """
    The official Context Clutch SDK for Python.
    Connect AI Agents (LangChain, AutoGen, Sierra) safely to raw execution environments.
    """
    def __init__(self, endpoint: str = "http://localhost:8000"):
        self.endpoint = endpoint.rstrip("/")
        self.client = httpx.Client(timeout=30.0)

    def execute(self, command: str) -> str:
        """
        Executes a raw bash command inside the secure Clutch sandbox. 
        Automatically truncates output via Drop-Files to protect the agent's context window.
        Returns the safe string output.
        """
        try:
            response = self.client.post(
                f"{self.endpoint}/v1/execute",
                json={"command": command}
            )
            response.raise_for_status()
            data = response.json()
            return data.get("output", str(data))
        except httpx.HTTPError as e:
            return f"Context Clutch Communication Error: The proxy firewall failed to connect - {str(e)}"
    
    def as_langchain_tool(self):
        """
        Returns a pre-configured LangChain Tool object.
        Drop this directly into your LangGraph or LangChain Agent.
        """
        try:
            from langchain.tools import Tool
            return Tool(
                name="Context_Clutch_Terminal",
                func=self.execute,
                description="Use this to execute terminal commands (bash, curl, python scripts) safely. Output is guaranteed to be token-safe. If output is too massive, it will return a drop-file path representing your data."
            )
        except ImportError:
            raise ImportError("Langchain is not installed. Run `pip install langchain` to use the helper.")

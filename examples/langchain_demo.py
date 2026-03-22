import os
from langchain.agents import initialize_agent, AgentType
from langchain.chat_models import ChatAnthropic # or ChatOpenAI
from context_clutch import ContextClutch

# 1. Initialize the Context Clutch Client pointing to your Docker container
clutch = ContextClutch(endpoint="http://localhost:8000")

# 2. Get the LangChain-compatible Tool
clutch_tool = clutch.as_langchain_tool()

# 3. Initialize your standard LLM (e.g., Claude 3)
llm = ChatAnthropic(model="claude-3-opus-20240229", temperature=0)

# 4. Give the agent the Context Clutch terminal tool
tools = [clutch_tool]

agent = initialize_agent(
    tools, 
    llm, 
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, 
    verbose=True
)

if __name__ == "__main__":
    print("Agent is starting. It will use Context Clutch to avoid context bloat.")
    
    # The Agent will use the tool to run this. If it outputs 50MB, the agent survives!
    result = agent.run("Find the largest file in the src directory and tell me what the first 5 functions are.")
    print("Final Result:", result)

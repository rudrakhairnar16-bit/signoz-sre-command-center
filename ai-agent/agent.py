from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from mcp_tool import query_signoz

@tool
def signoz_mcp(query: str) -> str:
    """Query SigNoz observability data about services, traces, logs, alerts, dashboards, metrics, and SLOs."""
    return query_signoz(query)


def create_agent(model: str = "llama3.2:3b"):
    llm = ChatOllama(
        model=model,
        temperature=0
    )
    tools = [signoz_mcp]
    agent = create_react_agent(llm, tools)
    return agent

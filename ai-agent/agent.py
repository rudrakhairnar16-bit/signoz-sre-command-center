from typing import Optional
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from mcp_tool import query_signoz

@tool
def signoz_mcp(query: str) -> str:
    """Query SigNoz observability data about services, traces, logs, alerts, dashboards, metrics, and SLOs."""
    return query_signoz(query)


def create_agent(openai_api_key: str, model: str = "gpt-4o-mini"):
    llm = ChatOpenAI(
        model=model,
        temperature=0,
        api_key=openai_api_key
    )
    tools = [signoz_mcp]
    agent = create_react_agent(llm, tools)
    return agent

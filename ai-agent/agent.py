from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from mcp_tool import query_signoz, remediate_service

@tool
def signoz_mcp(query: str) -> str:
    """Query SigNoz observability data about services, traces, logs, alerts, dashboards, metrics, and SLOs. Use this to check service health, find errors, or investigate issues."""
    return query_signoz(query)

@tool
def signoz_remediate(service: str) -> str:
    """Restart a failing service. Use this when a service is unhealthy, has high error rates, or needs recovery. Services: fastapi-svc, express-svc, goworker-svc."""
    return remediate_service(service)


def create_agent(model: str = "llama3.2:3b"):
    llm = ChatOllama(
        model=model,
        temperature=0
    )
    tools = [signoz_mcp, signoz_remediate]
    agent = create_react_agent(llm, tools)
    return agent

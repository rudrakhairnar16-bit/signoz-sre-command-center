import os
from dotenv import load_dotenv
load_dotenv()
from typing import Optional
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from mcp_tool import (
    list_services as _list_services,
    search_traces as _search_traces,
    search_logs as _search_logs,
    list_alerts as _list_alerts,
    list_dashboards as _list_dashboards,
    get_metrics as _get_metrics,
    search_docs as _search_docs,
    remediate_service as _remediate_service,
    predict_slo as _predict_slo,
)


@tool
def signoz_list_services(time_range: Optional[str] = None, limit: Optional[int] = None) -> str:
    """List all services monitored by SigNoz with their call rates, error rates, and latencies. Use time_range like '1h', '6h', '24h'."""
    return _list_services(time_range or "1h", limit or 50)


@tool
def signoz_search_traces(service_name: Optional[str] = None, time_range: Optional[str] = None, limit: Optional[int] = None) -> str:
    """Search traces in SigNoz. Optionally filter by service name. Use time_range like '1h', '6h', '24h'."""
    return _search_traces(service_name or "", time_range or "1h", limit or 10)


@tool
def signoz_search_logs(service_name: Optional[str] = None, time_range: Optional[str] = None, severity: Optional[str] = None, limit: Optional[int] = None) -> str:
    """Search logs in SigNoz. Optionally filter by service name and severity (e.g., ERROR, WARN, INFO). Use time_range like '1h', '6h', '24h'."""
    return _search_logs(service_name or "", time_range or "1h", severity or "", limit or 10)


@tool
def signoz_list_alerts() -> str:
    """List all configured alert rules in SigNoz with their severity and status."""
    return _list_alerts()


@tool
def signoz_list_dashboards() -> str:
    """List all dashboards configured in SigNoz."""
    return _list_dashboards()


@tool
def signoz_get_metrics(time_range: Optional[str] = None) -> str:
    """Get metrics from SigNoz including latency, P99, and request rates. Use time_range like '1h', '6h', '24h'."""
    return _get_metrics(time_range or "1h")


@tool
def signoz_search_docs(query_text: str, limit: Optional[int] = None) -> str:
    """Search SigNoz documentation for how-to guides, troubleshooting, and feature explanations."""
    return _search_docs(query_text, limit or 5)


@tool
def signoz_remediate(service: str) -> str:
    """Restart a failing service. Use this when a service has high error rates, is unhealthy, or needs recovery. Valid services: fastapi-svc, express-svc, goworker-svc."""
    return _remediate_service(service)


@tool
def signoz_predict_slo(service: Optional[str] = None) -> str:
    """Predict SLO breach risk for a specific service or all services. Shows burn rate, remaining error budget, and estimated time to SLO exhaustion. SLO target is 99.5%."""
    return _predict_slo(service or "")


def _get_llm():
    provider = os.environ.get("LLM_PROVIDER", "ollama").strip().lower()
    model = os.environ.get("LLM_MODEL", "")
    temperature = 0

    if provider == "groq":
        from langchain_groq import ChatGroq
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is required for Groq provider")
        return ChatGroq(
            model=model or "llama-3.3-70b-versatile",
            temperature=temperature,
            api_key=api_key,
        )

    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is required for Gemini provider")
        return ChatGoogleGenerativeAI(
            model=model or "gemini-2.0-flash-lite",
            temperature=temperature,
            api_key=api_key,
        )

    elif provider == "claude":
        from langchain_anthropic import ChatAnthropic
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for Claude provider")
        return ChatAnthropic(
            model=model or "claude-3-haiku-20240307",
            temperature=temperature,
            api_key=api_key,
        )

    elif provider in ("openai-compatible", "deepseek"):
        from langchain_openai import ChatOpenAI
        api_key = os.environ.get("OPENAI_API_KEY")
        base_url = os.environ.get("OPENAI_BASE_URL", "https://api.deepseek.com")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI-compatible provider")
        return ChatOpenAI(
            model=model or "deepseek-chat",
            temperature=temperature,
            api_key=api_key,
            base_url=base_url,
        )

    else:
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=model or "llama3.2:3b",
            temperature=temperature,
        )


def create_agent(model: str = ""):
    if model:
        os.environ.setdefault("LLM_MODEL", model)
    llm = _get_llm()
    provider = os.environ.get("LLM_PROVIDER", "ollama")
    print(f"Agent initialized with provider: {provider}, model: {llm.model}")
    tools = [
        signoz_list_services,
        signoz_search_traces,
        signoz_search_logs,
        signoz_list_alerts,
        signoz_list_dashboards,
        signoz_get_metrics,
        signoz_search_docs,
        signoz_remediate,
        signoz_predict_slo,
    ]
    agent = create_react_agent(llm, tools)
    return agent

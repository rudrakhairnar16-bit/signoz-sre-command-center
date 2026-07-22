import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
from typing import Optional, Any
from langchain_core.tools import tool
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
    """List all services monitored by SigNoz with their call rates, error rates, and latencies."""
    return _list_services(time_range or "1h", limit or 50)


@tool
def signoz_search_traces(service_name: Optional[str] = None, time_range: Optional[str] = None, limit: Optional[int] = None) -> str:
    """Search traces in SigNoz. Optionally filter by service name."""
    return _search_traces(service_name or "", time_range or "1h", limit or 10)


@tool
def signoz_search_logs(service_name: Optional[str] = None, time_range: Optional[str] = None, severity: Optional[str] = None, limit: Optional[int] = None) -> str:
    """Search logs in SigNoz. Optionally filter by service name and severity."""
    return _search_logs(service_name or "", time_range or "1h", severity or "", limit or 10)


@tool
def signoz_list_alerts() -> str:
    """List all configured alert rules in SigNoz."""
    return _list_alerts()


@tool
def signoz_list_dashboards() -> str:
    """List all dashboards configured in SigNoz."""
    return _list_dashboards()


@tool
def signoz_get_metrics(time_range: Optional[str] = None) -> str:
    """Get metrics from SigNoz including latency, P99, and request rates."""
    return _get_metrics(time_range or "1h")


@tool
def signoz_search_docs(query_text: str, limit: Optional[int] = None) -> str:
    """Search SigNoz documentation for how-to guides and troubleshooting."""
    return _search_docs(query_text, limit or 5)


@tool
def signoz_remediate(service: str) -> str:
    """Restart a failing service. Valid: fastapi-svc, express-svc, goworker-svc."""
    return _remediate_service(service)


@tool
def signoz_predict_slo(service: Optional[str] = None) -> str:
    """Predict SLO breach risk for a specific service or all services."""
    return _predict_slo(service or "")


TOOLS = [
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


class MockAgent:
    def invoke(self, state):
        prompt = state["messages"][-1][1] if isinstance(state["messages"][-1], tuple) else state["messages"][-1].content
        prompt_lower = prompt.lower()
        svc = ""
        for s in ["fastapi-svc", "express-svc", "goworker-svc"]:
            short = s.replace("-svc", "")
            if short in prompt_lower or s in prompt_lower:
                svc = s
                break
        if "trace" in prompt_lower:
            response = _search_traces(svc, "6h", 10)
        elif "log" in prompt_lower:
            sev = "ERROR" if "error" in prompt_lower else ""
            response = _search_logs(svc, "6h", sev, 10)
        elif "alert" in prompt_lower:
            response = _list_alerts()
        elif "dashboard" in prompt_lower:
            response = _list_dashboards()
        elif "metric" in prompt_lower or "p99" in prompt_lower or "latency" in prompt_lower:
            response = _get_metrics("6h")
        elif "predict" in prompt_lower or "slo" in prompt_lower:
            response = _predict_slo(svc)
        elif "restart" in prompt_lower or "remediate" in prompt_lower:
            response = _remediate_service(svc or "fastapi-svc")
        elif "doc" in prompt_lower or "how" in prompt_lower or "help" in prompt_lower:
            response = _search_docs(prompt, 3)
        elif "service" in prompt_lower:
            response = _list_services()
        else:
            response = _list_services()
        return {"messages": [{"content": response}]}


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

    elif provider == "ollama":
        import requests
        try:
            resp = requests.get("http://localhost:11434/api/tags", timeout=3)
            models = resp.json().get("models", [])
            model_names = [m["name"] for m in models]
            if not model_names:
                raise ValueError("Ollama is running but no models are installed. Run: ollama pull llama3.2:3b")
            chosen = model or "llama3.2:3b"
            if chosen not in model_names and "llama3.2:3b" in model_names:
                chosen = "llama3.2:3b"
            if chosen not in model_names:
                raise ValueError(f"Ollama model '{chosen}' not found. Available: {', '.join(model_names[:5])}")
        except requests.exceptions.ConnectionError:
            raise ValueError("Ollama server not reachable on localhost:11434")
        from langchain_ollama import ChatOllama
        return ChatOllama(model=chosen, temperature=temperature)

    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


def create_agent() -> Any:
    provider = os.environ.get("LLM_PROVIDER", "ollama")
    model = os.environ.get("LLM_MODEL", "")
    try:
        llm = _get_llm()
        print(f"Agent initialized with provider: {provider}, model: {llm.model}")
        from langgraph.prebuilt import create_react_agent
        return create_react_agent(llm, TOOLS)
    except Exception as e:
        print(f"LLM {provider} not available ({e}). Using direct tool agent as fallback.")
        return MockAgent()

import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
import streamlit as st
from agent import create_agent

st.set_page_config(
    page_title="SigNoz SRE Command Center",
    page_icon="📊",
    layout="wide"
)

agent = create_agent()
provider = os.environ.get("LLM_PROVIDER", "ollama")
model = os.environ.get("LLM_MODEL", "llama3.2:3b" if provider == "ollama" else "llama-3.3-70b-versatile")
use_llm = agent.__class__.__name__ != "MockAgent"

st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #e0e0e0; }
    .stChatMessage { background-color: #1a1d23; border-radius: 8px; padding: 12px; margin: 4px 0; border-left: 3px solid #00d4aa; }
    .stChatMessage[data-testid="user-message"] { border-left-color: #6c5ce7; }
    .stSidebar { background-color: #161a22; }
    .main-header { color: #00d4aa; font-size: 1.5rem; font-weight: 600; display: flex; align-items: center; gap: 10px; }
    .sub-header { color: #888; font-size: 0.9rem; margin-top: -10px; margin-bottom: 20px; }
    .status-badge { display: inline-block; padding: 2px 12px; border-radius: 12px; font-size: 0.75rem; font-weight: 500; }
    .badge-green { background-color: #00d4aa22; color: #00d4aa; border: 1px solid #00d4aa44; }
    .badge-purple { background-color: #6c5ce722; color: #a29bfe; border: 1px solid #6c5ce744; }
    .badge-orange { background-color: #fdcb6e22; color: #fdcb6e; border: 1px solid #fdcb6e44; }
    .query-category { color: #00d4aa; font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-top: 16px; margin-bottom: 4px; }
    .footer { color: #555; font-size: 0.7rem; text-align: center; margin-top: 40px; }
    div[data-testid="stChatInput"] input { background-color: #1a1d23; border: 1px solid #333; color: #e0e0e0; border-radius: 8px; }
    div[data-testid="stChatInput"] input:focus { border-color: #00d4aa; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header"> SigNoz SRE Command Center</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">AI-powered SLO monitoring · Predictive alerts · Auto-remediation</div>', unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_query" not in st.session_state:
    st.session_state.pending_query = None

with st.sidebar:
    st.markdown(f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px"> <span style="font-weight:600">System Status</span></div>', unsafe_allow_html=True)
    p_color = "badge-green" if use_llm else "badge-orange"
    mode = f"{provider}" if use_llm else "direct (no LLM)"
    st.markdown(f'<span class="status-badge {p_color}">Mode: {mode}</span>', unsafe_allow_html=True)
    st.markdown(f'<span class="status-badge badge-purple" style="margin-left:4px">{model if use_llm else "tool-only"}</span>', unsafe_allow_html=True)
    st.markdown("")

    if st.button("Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.markdown('<div class="query-category">Observability</div>', unsafe_allow_html=True)
    for q in ["What services are running?", "Show me traces from fastapi-svc", "Check ERROR logs for express-svc", "What are my p99 latencies?"]:
        if st.button(q, key=f"q-{q}", use_container_width=True):
            st.session_state.pending_query = q
            st.rerun()

    st.markdown('<div class="query-category">SLO & Predictions</div>', unsafe_allow_html=True)
    for q in ["Predict SLO for all services", "Predict SLO for fastapi-svc", "List all alert rules"]:
        if st.button(q, key=f"q-{q}", use_container_width=True):
            st.session_state.pending_query = q
            st.rerun()

    st.markdown('<div class="query-category">Remediation</div>', unsafe_allow_html=True)
    for q in ["Restart fastapi-svc", "Restart express-svc", "How do I create a dashboard?"]:
        if st.button(q, key=f"q-{q}", use_container_width=True):
            st.session_state.pending_query = q
            st.rerun()

    st.markdown('<div class="footer">SigNoz SRE Command Center v2.0</div>', unsafe_allow_html=True)

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

prompt = st.chat_input("Ask about your system...")
if st.session_state.pending_query:
    prompt = st.session_state.pending_query
    st.session_state.pending_query = None

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Querying SigNoz..."):
            try:
                result = agent.invoke({"messages": [("human", prompt)]})
                response = result["messages"][-1].content
            except Exception as e:
                response = str(e)
        st.markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})

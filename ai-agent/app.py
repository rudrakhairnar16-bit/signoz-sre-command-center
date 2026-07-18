import os
import streamlit as st
from agent import create_agent

st.set_page_config(
    page_title="SigNoz SRE Command Center - AI Agent",
    page_icon=":material/query_stats:",
    layout="wide"
)

st.title("SigNoz SRE Command Center - AI Agent")
st.markdown("Ask natural language questions about your system's health, performance, and errors.")

st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #e0e0e0; }
    .stChatMessage { background-color: #1a1d23; border-radius: 8px; padding: 12px; margin: 4px 0; }
    .stSidebar { background-color: #161a22; }
    .main-header { color: #00d4aa; font-size: 1.5rem; font-weight: 600; }
    .status-badge { display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 0.8rem; }
    .badge-green { background-color: #00d4aa22; color: #00d4aa; border: 1px solid #00d4aa44; }
</style>
""", unsafe_allow_html=True)

provider = os.environ.get("LLM_PROVIDER", "ollama")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent" not in st.session_state:
    st.session_state.agent = create_agent()
    st.sidebar.success(f"Agent ready (provider: {provider})")

if st.sidebar.button("Clear conversation"):
    st.session_state.messages = []
    st.rerun()

st.sidebar.markdown("### Example queries")
st.sidebar.markdown("- What services are running?")
st.sidebar.markdown("- Which service has the highest error rate?")
st.sidebar.markdown("- Show me traces from fastapi-svc")
st.sidebar.markdown("- Check ERROR logs for express-svc")
st.sidebar.markdown("- List all alert rules")
st.sidebar.markdown("- What are my p99 latencies?")
st.sidebar.markdown("- How do I create a dashboard?")
st.sidebar.markdown("- Restart fastapi-svc (remediation)")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask about your system..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if st.session_state.agent is None:
        response = "Agent not initialized. Please refresh the page."
    else:
        with st.chat_message("assistant"):
            with st.spinner("Querying SigNoz..."):
                try:
                    result = st.session_state.agent.invoke(
                        {"messages": [("human", prompt)]}
                    )
                    response = result["messages"][-1].content
                except Exception as e:
                    err_msg = str(e) if "GROQ_API_KEY" in str(e) or "API_KEY" in str(e) else "Something went wrong. Check that SigNoz MCP is running and your API key is valid."
                    response = f"⚠️ {err_msg}"
            st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})

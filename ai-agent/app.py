import streamlit as st
from agent import create_agent

st.set_page_config(
    page_title="SigNoz SRE Command Center - AI Agent",
    page_icon=":material/query_stats:",
    layout="wide"
)

st.title("SigNoz SRE Command Center - AI Agent")
st.markdown("Ask natural language questions about your system's health, performance, and errors.")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent" not in st.session_state:
    st.session_state.agent = create_agent("llama3.2:3b")
    st.sidebar.success("Agent ready (local LLM: llama3.2:3b)")

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
                    response = f"Error: {str(e)}"
            st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})

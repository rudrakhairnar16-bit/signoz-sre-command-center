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
    st.session_state.agent = None

api_key = st.sidebar.text_input("OpenAI API Key", type="password")
model = st.sidebar.selectbox("Model", ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"])

if api_key and st.session_state.agent is None:
    st.session_state.agent = create_agent(api_key, model)
    st.sidebar.success("Agent initialized!")

if st.sidebar.button("Clear conversation"):
    st.session_state.messages = []
    st.rerun()

st.sidebar.markdown("### Example queries")
st.sidebar.markdown("- What services are running?")
st.sidebar.markdown("- Show me error traces from the last hour")
st.sidebar.markdown("- What are my p99 latencies?")
st.sidebar.markdown("- List all active alerts")
st.sidebar.markdown("- How do I create a dashboard?")
st.sidebar.markdown("- Check logs for express-svc")
st.sidebar.markdown("- What is error budget and how is it calculated?")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask about your system..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if st.session_state.agent is None:
        response = "Please enter your OpenAI API key in the sidebar first."
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

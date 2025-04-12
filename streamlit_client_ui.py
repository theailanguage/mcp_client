# ============================
# IMPORTS
# ============================

# Streamlit is the core library used to build the interactive web app UI
# Install: pip install streamlit
import streamlit as st

# asyncio is used to run asynchronous I/O, especially for MCP tool communication
import asyncio

# os provides filesystem interaction like checking if files exist or reading directories
import os

# json is used to read and write conversation data to JSON files
import json

# datetime is used to timestamp conversation logs and messages
import datetime

# nest_asyncio allows nested use of asyncio event loops, useful in interactive notebooks or Streamlit
# Install: pip install nest_asyncio
import nest_asyncio

# PIL (Python Imaging Library) is used to load, crop, and style images like the logo
# Install: pip install pillow
from PIL import Image, ImageOps, ImageDraw

# HTML components for more advanced customization (not used directly here but imported if needed)
from streamlit.components.v1 import html

# Allow asyncio event loop reuse (important for Streamlit apps that rerun on input change)
nest_asyncio.apply()


# ============================
# SESSION STATE INITIALIZATION
# ============================

# Initialize conversation list if not already present in session state
if "conversation" not in st.session_state:
    st.session_state.conversation = []

# Default config dict for selecting between client types and config files
if "client_config" not in st.session_state:
    st.session_state.client_config = {
        "client_type": "STDIO",
        "server_url": "",
        "stdio_config": None
    }

# Placeholder for reusable client object (SSE, not implemented here)
if "client_instance" not in st.session_state:
    st.session_state.client_instance = None

# Theme toggle (not used yet, but initialized)
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

# List to store logs for user debug/tracing
if "logs" not in st.session_state:
    st.session_state.logs = []

# Trigger to identify form submission via Enter key
if "submit_triggered" not in st.session_state:
    st.session_state.submit_triggered = False

# Flag to prevent infinite rerun loops after processing a query
if "query_executed" not in st.session_state:
    st.session_state.query_executed = False

# Holds the current query to be executed after submission
if "pending_query" not in st.session_state:
    st.session_state.pending_query = ""


# ============================
# UTILITY FUNCTIONS
# ============================

# Run a coroutine in an event loop; fallback for environments like Streamlit
def run_async_in_event_loop(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)

    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result()

# Logging utility: logs messages with timestamp to both console and UI logs
def add_log(message: str):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"{timestamp} - {message}"
    st.session_state.logs.append(log_message)
    print(log_message)


# ============================
# SIDEBAR: SETTINGS & LOG VIEW
# ============================

with st.sidebar:
    st.header("Settings")

    # Client selection (only STDIO is implemented currently)
    client_type = st.radio("Select Client Type:", options=["STDIO", "SSE (not implemented)"], index=0)
    st.session_state.client_config["client_type"] = client_type
    add_log(f"Client type set to: {client_type}")

    # STDIO: Load config.json or fallback to default
    uploaded_file = st.file_uploader("Upload config.json for STDIO", type="json")
    if uploaded_file is not None:
        config_path = "theailanguage_config.json"
        with open(config_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success("STDIO config saved as theailanguage_config.json")
        st.session_state.client_config["stdio_config"] = config_path
        add_log(f"STDIO config uploaded and saved as: {config_path}")
    else:
        default_config = "theailanguage_config.json"
        if os.path.exists(default_config):
            st.info(f"Using default config: {default_config}")
            st.session_state.client_config["stdio_config"] = default_config
            add_log(f"Using default STDIO config: {default_config}")
        else:
            st.warning("No STDIO config provided and default file 'theailanguage_config.json' not found.")
            add_log("No STDIO config found.")

    st.markdown("---")
    st.header("Load Conversation")

    # List and allow loading previous conversations
    conversations_dir = "conversations"
    os.makedirs(conversations_dir, exist_ok=True)
    conversation_files = os.listdir(conversations_dir)
    if conversation_files:
        for filename in conversation_files:
            filepath = os.path.join(conversations_dir, filename)
            with open(filepath, "r") as f:
                conv = json.load(f)
            preview = conv[0]["message"][:20] if conv else "No message"
            if st.button(f"Load {filename}"):
                st.session_state.conversation = conv
                st.success(f"Loaded conversation from {filename}")
                add_log(f"Loaded conversation from {filename}")
    else:
        st.info("No saved conversations found.")

    st.markdown("---")
    with st.expander("Log Output"):
        st.text_area("Logs", "\n".join(st.session_state.logs), height=200)


# ============================
# MAIN CHAT UI
# ============================

# Render circular logo and title
col1, col2 = st.columns([1, 6])
with col1:
    raw_logo = Image.open("assets/logo.jpg")
    size = min(raw_logo.size)
    mask = Image.new('L', (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)
    circular_logo = ImageOps.fit(raw_logo, (size, size), centering=(0.5, 0.5))
    circular_logo.putalpha(mask)
    st.image(circular_logo, use_container_width=True)

with col2:
    st.title("The AI Language - MCP Client")

# Render YouTube call to action as clickable link
st.markdown(
    "[**Subscribe to our YouTube – Get Free Access to Code. Click Here!**](https://youtube.com/@theailanguage?sub_confirmation=1)",
    unsafe_allow_html=True
)

# Show past conversation
for msg in st.session_state.conversation:
    timestamp = msg.get("timestamp", "")
    sender = msg.get("sender", "")
    message = msg.get("message", "")
    st.markdown(f"**[{timestamp}] {sender}:** {message}")

# Callback function: sets the submit_triggered flag when enter is pressed
def submit_on_enter():
    if st.session_state.query_input.strip():
        st.session_state.submit_triggered = True
        st.session_state.pending_query = st.session_state.query_input

# Input box: on pressing enter, triggers the callback
st.text_input(
    "Your Query:",
    key="query_input",
    placeholder="Type your query here",
    on_change=submit_on_enter
)

# Buttons for sending message, starting new conversation, and saving conversation
send_button = st.button("Send")
new_conv_button = st.button("\U0001F4DD New Conversation")
save_conv_button = st.button("\U0001F4BE Save Conversation")


# ============================
# CORE LOGIC FOR QUERY HANDLING
# ============================

# Async function that uses the STDIO backend to fetch a response
async def process_query_stdio(query: str) -> str:
    add_log("Processing query in STDIO mode.")
    try:
        from streamlit_client_stdio import run_agent
    except ImportError as e:
        add_log(f"Error importing run_agent: {e}")
        return f"Error importing run_agent: {e}"

    result = await run_agent(query)
    add_log("STDIO query processed.")
    return result

# Append user and assistant messages, and mark query executed
async def handle_query(query: str):
    if query.strip().lower() == "quit":
        st.session_state.conversation = []
        add_log("Conversation reset (quit command).")
    else:
        user_ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.session_state.conversation.append({
            "sender": "User",
            "message": query,
            "timestamp": user_ts
        })
        add_log(f"User query appended: {query}")
        response_text = await process_query_stdio(query)
        st.session_state.conversation.append({
            "sender": "MCP",
            "message": response_text,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        add_log("MCP response appended to conversation.")
        st.session_state.query_executed = True


# ============================
# MAIN TRIGGER LOGIC
# ============================

# Check for send button or enter key press, and ensure rerun doesn't loop
if (send_button or st.session_state.submit_triggered) and not st.session_state.query_executed:
    query = st.session_state.pending_query.strip()
    if query:
        run_async_in_event_loop(handle_query(query))
        st.session_state.submit_triggered = False

# Rerun Streamlit app after query completes to refresh UI
if st.session_state.query_executed:
    st.session_state.query_executed = False
    st.rerun()

# New conversation
if new_conv_button:
    st.session_state.conversation = []
    add_log("New conversation started.")
    st.rerun()

# Save conversation to a file
if save_conv_button:
    conversations_dir = "conversations"
    os.makedirs(conversations_dir, exist_ok=True)
    filename = f"conversation_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.json"
    filepath = os.path.join(conversations_dir, filename)
    with open(filepath, "w") as f:
        json.dump(st.session_state.conversation, f, indent=2)
    add_log(f"Conversation saved as {filename}.")
    st.success(f"Conversation saved as {filename}")

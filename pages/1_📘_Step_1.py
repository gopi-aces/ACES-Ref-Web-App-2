import streamlit as st
import openai
import json
import os
import time
import shutil
from langchain.text_splitter import RecursiveCharacterTextSplitter
from utils import load_settings  # Import shared functions

# Constants
SESSION_DIR = "sessions"  # Directory to store session data
INACTIVITY_LIMIT = 1020  # Time limit in seconds (e.g., 1 hour)

# Ensure session directory exists
os.makedirs(SESSION_DIR, exist_ok=True)

def setup_openai():
    """Set up OpenAI API configuration."""
    openai.api_key = st.secrets["OPENAI_API_KEY"]

def clean_up_sessions():
    """Remove session directories older than the inactivity limit."""
    current_time = time.time()
    for session_folder in os.listdir(SESSION_DIR):
        session_path = os.path.join(SESSION_DIR, session_folder)
        if os.path.isdir(session_path):
            timestamp_file = os.path.join(session_path, "last_active.txt")
            if os.path.exists(timestamp_file):
                with open(timestamp_file, "r") as f:
                    last_active = float(f.read())
                if current_time - last_active > INACTIVITY_LIMIT:
                    shutil.rmtree(session_path)


def update_last_active(session_id):
    """Update the last active timestamp for the session."""
    session_path = os.path.join(SESSION_DIR, session_id)
    os.makedirs(session_path, exist_ok=True)
    with open(os.path.join(session_path, "last_active.txt"), "w") as f:
        f.write(str(time.time()))


def initialize_session():
    """Initialize session management."""
    if "session_id" not in st.session_state:
        st.session_state.session_id = f"session_{int(time.time())}"
    update_last_active(st.session_state.session_id)


def load_history(session_id):
    """Load chat history for the session."""
    session_path = os.path.join(SESSION_DIR, session_id)
    history_file = os.path.join(session_path, "chat_history.json")
    if os.path.exists(history_file):
        with open(history_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return [{"role": "system", "content": SYSTEM_MESSAGE["content"]}]


def save_history(session_id, history):
    """Save chat history for the session."""
    session_path = os.path.join(SESSION_DIR, session_id)
    history_file = os.path.join(session_path, "chat_history.json")
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=4)


# Hide Streamlit style
hide_st_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
"""
st.markdown(hide_st_style, unsafe_allow_html=True)

SYSTEM_MESSAGE = {
    "role": "system",
    "content": """
You are a reference formatting assistant specialized in converting academic references into the correct BibTeX format.

Please follow these guidelines:

1. Use the BibTeX format for each reference.
2. Each entry has a unique citation key. Ensure that these keys are unique across your entire BibTeX file to avoid conflicts when citing.
3. Start each entry with the correct BibTeX type (e.g., `@article`, `@book`, `@inbook`, `@incollection`, `@misc`, `@phdthesis`, `@inproceedings`, `@unpublished`, etc.).
4. Ensure that each reference follows this structure:

@article{reference_key, author = {Author Name and Another Author}, title = {Title of the Paper}, journal = {Abbrivated Journal Name}, year = {Year}, volume = {Volume}, number = {Issue Number}, pages = {Page Range}, doi = {DOI Number}, url = {URL if available} }

5. Skip empty fields, and exclude any missing information.
6. Respond only with the BibTeX formatted output without any additional commentary or explanation.
"""
}


def BibTeX_abbr_New():
    st.title('✍️ ACES Ref. Tool')

    settings = load_settings()
    current_model = settings["model"]

    # Initialize session and clean up old sessions
    initialize_session()
    clean_up_sessions()

    # Load or initialize chat history
    session_id = st.session_state.session_id
    history = load_history(session_id)

    if st.button("Delete All History Except First Message"):
        history = [{"role": "system", "content": SYSTEM_MESSAGE["content"]}]
        save_history(session_id, history)
        st.success("Chat history trimmed to keep only the first message.")

    for message in history:
        if message["role"] != "system":
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    user_prompt = st.chat_input("👉 Enter your Refs...")

    if user_prompt:
        st.chat_message("user").markdown(user_prompt)
        history.append({"role": "user", "content": user_prompt})

        input_chunks = RecursiveCharacterTextSplitter(
            chunk_size=3000, chunk_overlap=100).split_text(user_prompt)

        setup_openai()
        combined_response = ""

        try:
            for chunk in input_chunks:
                response = openai.ChatCompletion.create(
                    model=current_model,
                    messages=history + [{"role": "user", "content": chunk}],
                    stream=True
                )

                assistant_response_stream = ""
                for part in response:
                    if "choices" in part:
                        delta = part["choices"][0]["delta"]
                        if "content" in delta:
                            assistant_response_stream += delta["content"]

                combined_response += assistant_response_stream

            with st.chat_message("assistant"):
                st.markdown(f"```bibtex\n{combined_response}\n```")

            history.append({"role": "assistant", "content": combined_response})
            save_history(session_id, history)

        except openai.error.InvalidRequestError as e:
            st.error(f"Invalid request error: {e}")
        except openai.error.OpenAIError as e:
            st.error(f"OpenAI error: {e}")
        except Exception as e:
            st.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    BibTeX_abbr_New()

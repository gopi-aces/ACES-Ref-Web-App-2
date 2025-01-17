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
1. Retain the original labels exactly as they appear in the input BibTeX (whether they are numeric or text-based).
2. **Spacing Between Initials**: Use a tilde (~) for spacing between initials in the author tag. Example: 

@article{50,
  author = {J.~H.~Kim and J.~R.~Ryu and others},
  title = {Frontiers in Neuroanatomy},
  journal = {Frontiers in Neuroanatomy},
  year = {2021},
  volume = {15},
  number = {},
  pages = {746057},
  doi = {},
  url = {}
} 

3. Convert the references into BibTeX format, replacing "et al." with "and others".
4. Convert the references into BibTeX format and enclose accented characters in curly braces to preserve them.
5. Start each entry with the correct BibTeX type (e.g., `@article`, `@book`, `@inbook`, `@incollection`, `@misc`, `@phdthesis`, `@inproceedings`, `@unpublished`, etc.).
6. Ensure that each reference follows this structure:

@article{Same_reference_key, author = {Author Name and Another Author}, title = {Title of the Paper}, journal = {Abbrivated Journal Name}, year = {Year}, volume = {Volume}, number = {Issue Number}, pages = {Page Range}, doi = {DOI Number}, url = {URL if available} }
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

    if st.button("Delete All History"):
        history = [{"role": "system", "content": SYSTEM_MESSAGE["content"]}]
        save_history(session_id, history)
        st.success("Deleted.")

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
            with st.spinner(text="In progress..."):
                time.sleep(4)
                st.success("Done!")
                for chunk in input_chunks:
                    # ChatCompletion with OpenAI API
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

            # Display the formatted BibTeX content
            with st.chat_message("assistant"):
                st.markdown(f"```bibtex\n{combined_response}\n```")

            # Append assistant response to history
            history.append({"role": "assistant", "content": combined_response})
            save_history(session_id, history)

            # Trigger balloons after displaying the BibTeX content
            st.balloons()


        except openai.error.InvalidRequestError as e:
            st.error(f"Invalid request error: {e}")
        except openai.error.OpenAIError as e:
            st.error(f"OpenAI error: {e}")
        except Exception as e:
            st.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    BibTeX_abbr_New()

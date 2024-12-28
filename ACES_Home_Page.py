import streamlit as st
import os
import time
import shutil

hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """


st.markdown(hide_st_style, unsafe_allow_html=True)

# Constants
SESSION_DIR = "sessions"  # Directory to store session data
INACTIVITY_LIMIT = 1120  # Time limit in seconds (e.g., 1 hour)

# Ensure session directory exists
os.makedirs(SESSION_DIR, exist_ok=True)

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

def main():
    clean_up_sessions()
    initialize_session()
    st.title("ACES Home Page")
    st.write("Welcome to the ACES application.")
    st.markdown("""
    This tool helps you format and manage academic references effortlessly.

    ### Features:
    - Step 1: Convert references into Tag format.
    - Step 2: Generate WS style References.
    """)

    update_last_active(st.session_state.session_id)

if __name__ == "__main__":
    main()

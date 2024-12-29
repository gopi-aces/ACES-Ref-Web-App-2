import streamlit as st
import os
import time
import uuid
from streamlit_ace import st_ace
import subprocess
import threading

# Configurations
session_activity = {}
user_to_session = {}
lock = threading.Lock()  # For concurrency handling
INACTIVITY_LIMIT = 1000  # Time limit in seconds (e.g., 1 hour)

# Helper function to generate a unique user ID
def get_user_id():
    if "user_id" not in st.session_state:
        st.session_state["user_id"] = str(uuid.uuid4())
    return st.session_state["user_id"]

# Function to manage session IDs
def get_session_id(user_id):
    global session_activity, user_to_session

    with lock:
        # Reuse existing session if user already has one
        if user_id in user_to_session:
            session_id = user_to_session[user_id]
            session_activity[session_id]['timestamp'] = time.time()
            return session_id

        # Generate a new session ID using int(time.time())
        session_id = int(time.time())
        session_activity[session_id] = {'user_id': user_id, 'timestamp': time.time()}
        user_to_session[user_id] = session_id
        return session_id

# Function to clean up expired session files
# Function to clean up expired session files based on inactivity
def cleanup_expired_sessions(expiry_time=INACTIVITY_LIMIT):
    current_time = time.time()
    expired_sessions = [
        sid for sid, data in session_activity.items()
        if current_time - data['timestamp'] > expiry_time
    ]

    for sid in expired_sessions:
        # Remove session files
        for ext in ['.dvi', '.aux', '.log', '.bbl', '.blg', '.bib', '.tex', '.out']:
            try:
                os.remove(f"{sid}-testbib{ext}")
            except FileNotFoundError:
                pass
        # Remove session metadata
        user_id = session_activity[sid]['user_id']
        user_to_session.pop(user_id, None)
        session_activity.pop(sid, None)
        print(f"Session {sid} cleaned up due to inactivity.")

# Page logic
def generate_bbl_page():
    st.title('BibTeX to BBL Generator')

    # Get the current user's unique ID and session ID
    user_id = get_user_id()
    session_id = get_session_id(user_id)

    st.info(f"Your Session ID: {session_id}")

    # Check for inactive sessions and clean them up
    cleanup_expired_sessions()

    # Define file names for this session
    tex_file = f'{session_id}-testbib.tex'
    bib_file = f'{session_id}-temp.bib'
    bbl_file = f'{session_id}-testbib.bbl'
    blg_file = f'{session_id}-testbib.blg'
    log_file = f'{session_id}-testbib.log'
    aux_file = f'{session_id}-testbib.aux'


    # Interface for BibTeX to BBL conversion
    bst_folder = 'bst'
    if not os.path.exists(bst_folder):
        st.error(f"Folder '{bst_folder}' not found. Please create the folder and add .bst files.")
    else:
        bst_files = [f for f in os.listdir(bst_folder) if f.endswith('.bst')]
        if not bst_files:
            st.error("No .bst files found in the 'bst' folder.")
        else:
            selected_bst = st.selectbox('Choose a .bst file', bst_files)

            st.subheader('Paste your BibTeX content below:')
            bib_content = st_ace(language='latex', theme='github', height=400)

            if st.button('Generate .bbl'):
                if bib_content:
                    # Save BibTeX content to a session-specific .bib file
                    with open(bib_file, 'w', encoding='utf-8') as f:
                        f.write(bib_content)

                    # Create LaTeX document content
                    tex_content = f"""
                    \\documentclass{{article}}
                    \\usepackage{{cite}}
                    \\usepackage{{hyperref}}
                    \\usepackage[utf8]{{inputenc}}
                    \\usepackage[T1]{{fontenc}}
                    \\usepackage{{amsmath,amssymb,amsfonts}}
                    \\begin{{document}}
                    \\cite{{*}}
                    \\bibliographystyle{{bst/{selected_bst}}}
                    \\bibliography{{{session_id}-temp}}
                    \\end{{document}}
                    """

                    # Save the session-specific .tex file
                    with open(tex_file, 'w', encoding='utf-8') as tex_file_obj:
                        tex_file_obj.write(tex_content)

                    # Docker commands for pdflatex and bibtex
                    docker_pdflatex_command = [
                        'docker', 'exec',
                        'miktex-container',
                        'latex', f"/miktex/work/{tex_file}"
                    ]

                    docker_bibtex_command = [
                        'docker', 'exec',
                        'miktex-container',
                        'bibtex', f"/miktex/work/{session_id}-testbib"
                    ]

                    try:
                        # Run Docker commands for LaTeX and BibTeX
                        subprocess.run(docker_pdflatex_command, check=True)
                        time.sleep(2)
                        subprocess.run(docker_bibtex_command, check=True)
                        time.sleep(2)

                        # Read and display the generated .bbl content
                        with open(bbl_file, 'r', encoding='utf-8') as bbl_file_obj:
                            bbl_content = bbl_file_obj.read()

                        st.subheader('Generated Output:')
                        st.markdown(f"```\n{bbl_content}\n```")
                    except subprocess.CalledProcessError as e:
                        st.error(f"An error occurred while running Docker LaTeX commands:\n{e}")
                        # Show the LaTeX and BibTeX logs if they exist
                        if os.path.exists(log_file):
                            with open(log_file, 'r', encoding='utf-8') as tex_log_file:
                                with st.expander("View LaTeX Log Output"):
                                    st.code(tex_log_file.read())
                        if os.path.exists(blg_file):
                            with open(blg_file, 'r', encoding='utf-8') as bib_log_file:
                                with st.expander("View BibTeX Log Output"):
                                    st.code(bib_log_file.read())
                else:
                    st.warning("Please provide BibTeX content before generating the file.")

    # Cleanup expired sessions (optional feature)
    cleanup_expired_sessions()

# Call the function to generate the page
generate_bbl_page()

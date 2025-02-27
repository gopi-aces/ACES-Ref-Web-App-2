import streamlit as st
import os
import time
import uuid
from streamlit_ace import st_ace
import subprocess
import threading

# Hide default Streamlit elements
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# Configurations
session_activity = {}
user_to_session = {}
lock = threading.Lock()  # For concurrency handling
INACTIVITY_LIMIT = 60  # 60 seconds for testing

# Helper function to generate a unique user ID
def get_user_id():
    if "user_id" not in st.session_state:
        st.session_state["user_id"] = str(uuid.uuid4())
    return st.session_state["user_id"]

# Function to manage session IDs
def get_session_id(user_id):
    global session_activity, user_to_session

    with lock:
        if user_id in user_to_session:
            session_id = user_to_session[user_id]
            session_activity[session_id]['timestamp'] = time.time()
            return session_id

        # Generate a new session ID
        session_id = int(time.time())
        session_activity[session_id] = {'user_id': user_id, 'timestamp': time.time()}
        user_to_session[user_id] = session_id
        return session_id

# Function to clean up expired session files
def cleanup_expired_sessions():
    current_time = time.time()
    expired_sessions = []

    # Identify expired sessions
    with lock:
        #print("Current time:", current_time)
        for sid, data in session_activity.items():
            #print(f"Session ID: {sid}, Last Activity: {data['timestamp']}, Inactive Duration: {current_time - data['timestamp']}")
            if current_time - data['timestamp'] > INACTIVITY_LIMIT:
                expired_sessions.append(sid)

    #print("Expired sessions:", expired_sessions)

    # Remove files associated with expired sessions
    for sid in expired_sessions:
        for ext in ['.dvi', '.aux', '.log', '.bbl', '.blg', '.bib', '.tex', '.out']:
            file_path = f"{sid}-testbib{ext}"
            file_path1 = f"{sid}-temp{ext}"

            # Delete {sid}-testbib{ext}
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"Deleted: {file_path}")
                except Exception as e:
                    print(f"Error deleting {file_path}: {e}")

            # Delete {sid}-temp{ext}
            if os.path.exists(file_path1):
                try:
                    os.remove(file_path1)
                    print(f"Deleted: {file_path1}")
                except Exception as e:
                    print(f"Error deleting {file_path1}: {e}")

        # Clean session data
        with lock:
            user_id = session_activity[sid]['user_id']
            user_to_session.pop(user_id, None)
            session_activity.pop(sid, None)
            #print(f"Cleaned up session {sid}")

# Periodic cleanup thread function
def periodic_cleanup():
    while True:
        cleanup_expired_sessions()
        time.sleep(5)  # Check every 5 seconds

# Start periodic cleanup in a separate thread
cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
cleanup_thread.start()

# Page logic
def generate_bbl_page():
    st.title('WS Style Reference Generator')

    # Get the current user's unique ID and session ID
    user_id = get_user_id()
    session_id = get_session_id(user_id)

    # Define session-specific file names
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
        bst_files = [f[:-4] for f in os.listdir(bst_folder) if f.endswith('.bst')]
        if not bst_files:
            st.error("No .bst files found in the 'bst' folder.")
        else:
            # Assuming bst_files is already populated with your .bst file names
            search_term = st.text_input("Search for your style:")
            filtered_bst_files = [file for file in bst_files if search_term.lower() in file.lower()]

            if filtered_bst_files:  # Check if there are any filtered results
                selected_bst = st.selectbox('Choose Your Style', filtered_bst_files)
            else:
                st.warning("No styles found matching your search.")

            st.subheader('Paste your Step 1 content below:')
            bib_content = st_ace(language='latex', theme='github', height=400)

            if st.button('Generate Ref'):
                if bib_content:
                    # Save BibTeX content
                    with open(bib_file, 'w', encoding='utf-8') as f:
                        f.write(bib_content)

                    # LaTeX content
                    tex_content = f"""
                    \\documentclass{{article}}
                    \\usepackage{{cite}}
                    \\begin{{document}}
                    \\nocite{{*}}
                    \\bibliographystyle{{bst/{selected_bst}}}
                    \\bibliography{{{session_id}-temp}}
                    \\end{{document}}
                    """

                    with open(tex_file, 'w', encoding='utf-8') as tex_file_obj:
                        tex_file_obj.write(tex_content)

                    # Docker commands for compilation
                    docker_pdflatex_command = [
                        'docker', 'exec', 'miktex-container',
                        'latex', f"/miktex/work/{tex_file}"
                    ]
                    docker_bibtex_command = [
                        'docker', 'exec', 'miktex-container',
                        'bibtex', f"/miktex/work/{session_id}-testbib"
                    ]

                    try:
                        # Run Docker commands for LaTeX and BibTeX
                        subprocess.run(docker_pdflatex_command, check=True)
                        time.sleep(2)
                        subprocess.run(docker_bibtex_command, check=True)
                        time.sleep(2)

                        # Check if .bbl file exists and display its content
                        if os.path.exists(bbl_file) and os.path.getsize(bbl_file) > 0:
                            with open(bbl_file, 'r', encoding='utf-8') as bbl_file_obj:
                                bbl_content = bbl_file_obj.read()

                            st.subheader('Generated Output:')
                            st.markdown(f"```latex\n{bbl_content}\n```")
                        else:
                            st.warning("The .bbl file was not generated or is empty.")
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

                        # Attempt to show .bbl content if it exists
                        if os.path.exists(bbl_file) and os.path.getsize(bbl_file) > 0:
                            with open(bbl_file, 'r', encoding='utf-8') as bbl_file_obj:
                                bbl_content = bbl_file_obj.read()

                            st.subheader('Generated Output (despite errors):')
                            st.markdown(f"```latex\n{bbl_content}\n```")
                    else:
                        st.warning("Please provide BibTeX content before generating the file.")

# Run the main page logic
generate_bbl_page()

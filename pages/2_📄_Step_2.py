import streamlit as st
import os
import subprocess
from streamlit_ace import st_ace
import time

# Hide Streamlit style elements
hide_st_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
"""
st.markdown(hide_st_style, unsafe_allow_html=True)

SESSION_DIR = "sessions"

def check_session():
    """Ensure the session is active."""
    if "session_id" not in st.session_state:
        st.error("Session not initialized. Please go back to the home page.")
        st.stop()
    session_path = os.path.join(SESSION_DIR, st.session_state.session_id)
    os.makedirs(session_path, exist_ok=True)
    with open(os.path.join(session_path, "last_active.txt"), "w") as f:
        f.write(str(time.time()))

def generate_bbl_page():
    check_session()
    st.title('Copy Past Step 1 data...')

    # Define the filenames for logs to be deleted
    log_file = 'testbib.log'
    aux_file = 'testbib.aux'

    # Add a button to clear only the log and aux files
    if st.button('Clear .log and .aux Files'):
        for file in [log_file, aux_file]:
            if os.path.exists(file):
                os.remove(file)
        st.success("Log (.log) and auxiliary (.aux) files have been deleted successfully!")

    # Display the main interface for BibTeX to BBL conversion
    bst_folder = 'bst'
    if not os.path.exists(bst_folder):
        st.error(f"Folder '{bst_folder}' not found. Please create the folder and add .bst files.")
    else:
        bst_files = [f for f in os.listdir(bst_folder) if f.endswith('.bst')]
        if not bst_files:
            st.error("No .bst files found in the 'bst' folder.")
        else:
            selected_bst = st.selectbox('Choose a .bst file', bst_files)

            st.subheader('Paste your Step 1 content below:')
            bib_content = st_ace(language='latex', theme='github', height=500)

            if st.button('Generate .bbl'):
                if bib_content:
                    # Set up file paths
                    current_dir = "/mnt/d/Python/2023/11-Nov/ACES-Ref-Web-App"
                    bib_file = 'temp.bib'
                    tex_file = 'testbib.tex'
                    bbl_file = 'testbib.bbl'
                    blg_file = 'testbib.blg'

                    # Save BibTeX content to a .bib file using UTF-8 encoding
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
                    \\bibliography{{temp}}
                    \\end{{document}}
                    """

                    # Save the .tex file using UTF-8 encoding
                    with open(tex_file, 'w', encoding='utf-8') as tex_file_obj:
                        tex_file_obj.write(tex_content)

                    # Docker commands for pdflatex and bibtex
                    docker_pdflatex_command = [
                        'docker', 'exec',
                        'miktex-container',  # Use the container name
                        'latex', '/miktex/work/testbib.tex'
                    ]

                    docker_bibtex_command = [
                        'docker', 'exec',
                        'miktex-container',
                        'bibtex', f"/miktex/work/testbib"
                    ]

                    try:
                        # Run Docker commands for LaTeX and BibTeX
                        subprocess.run(docker_pdflatex_command, check=True)
                        subprocess.run(docker_bibtex_command, check=True)

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
                                st.text("LaTeX Log Output:")
                                st.code(tex_log_file.read())
                        if os.path.exists(blg_file):
                            with open(blg_file, 'r', encoding='utf-8') as bib_log_file:
                                st.text("BibTeX Log Output:")
                                st.code(bib_log_file.read())
                else:
                    st.warning("Please provide Step 1 content before generating the file.")

# Call the function to generate the page
generate_bbl_page()

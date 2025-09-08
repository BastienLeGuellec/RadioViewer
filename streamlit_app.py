import streamlit as st
from pathlib import Path
import pandas as pd
from datetime import datetime
import json
import os

# --- Configuration ---
DATA_DIR = Path("data")
USERS_FILE = Path("users.xlsx")
DIAGNOSES_FILE = Path("diagnoses.json")
LOGS_DIR = Path("logs")
st.set_page_config(layout="wide", page_title="Radiology Case Viewer")

def initialize_admin_user():
    """
    Checks if the 'is_admin' column exists in the users file.
    If not, it adds the column and sets the first user as an admin.
    """
    if USERS_FILE.exists():
        users_df = pd.read_excel(USERS_FILE)
        if 'is_admin' not in users_df.columns:
            users_df['is_admin'] = False
            users_df.loc[0, 'is_admin'] = True
            users_df.to_excel(USERS_FILE, index=False)

# --- Logging Function ---
def log_action(username, action, case="", series="", details=""):
    """Appends a log entry to the specified Excel file."""
    LOGS_DIR.mkdir(exist_ok=True)
    log_file = LOGS_DIR / f"{username}_action_log.xlsx"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    columns=['Timestamp', 'Username', 'Action', 'Case', 'Series', 'Details']
    new_log_entry = pd.DataFrame([[timestamp, username, action, case, series, details]], columns=columns)
    
    try:
        if log_file.exists():
            log_df = pd.read_excel(log_file)
            # Ensure columns match, if not, create new file
            if list(log_df.columns) != columns:
                log_df = new_log_entry
            else:
                log_df = pd.concat([log_df, new_log_entry], ignore_index=True)
        else:
            log_df = new_log_entry
        
        log_df.to_excel(log_file, index=False)

    except Exception as e:
        st.sidebar.error(f"Log Error: {e}")

# --- Data Loading Functions ---

@st.cache_data
def load_users():
    """Loads user data from the excel file."""
    if not USERS_FILE.exists():
        st.error(f"User file not found at {USERS_FILE}")
        return None
    return pd.read_excel(USERS_FILE)

def load_diagnoses():
    """Loads diagnoses from the JSON file."""
    if not DIAGNOSES_FILE.exists():
        return {}
    with open(DIAGNOSES_FILE, 'r') as f:
        return json.load(f)

def save_diagnoses(data):
    """Saves diagnoses to the JSON file."""
    with open(DIAGNOSES_FILE, 'w') as f:
        json.dump(data, f, indent=4)

@st.cache_data
def get_cases():
    """Scans the data directory and returns a sorted list of case names."""
    if not DATA_DIR.is_dir():
        return []
    return sorted([d.name for d in DATA_DIR.iterdir() if d.is_dir()])

@st.cache_data
def get_series_for_case(case_name):
    """Returns a sorted list of series for a given case."""
    case_path = DATA_DIR / case_name
    if not case_path.is_dir():
        return []
    return sorted([d.name for d in case_path.iterdir() if d.is_dir()])

@st.cache_data
def get_images_for_series(case_name, series_name):
    """Returns a sorted list of image paths for a given series."""
    series_path = DATA_DIR / case_name / series_name
    if not series_path.is_dir():
        return []
    images = [f for f in series_path.iterdir() if f.suffix.lower() in ('.jpg', '.jpeg', '.png')]
    def sort_key(path):
        try: return int(path.stem)
        except (ValueError, TypeError): return path.name
    return sorted(images, key=sort_key)

# --- Page Drawing Functions ---

def draw_login_page():
    st.title("Radiology Viewer Login")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("logo.png", use_column_width=True)

    users_df = load_users()
    if users_df is None: return

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

        if submitted:
            user_record = users_df[users_df['username'] == username]
            if not user_record.empty and str(user_record.iloc[0]['password']) == password:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.is_admin = user_record.iloc[0].get('is_admin', False)
                st.session_state.page = "case_selection"
                log_action(username, "Login Success")
                st.rerun()
            else:
                st.error("Invalid username or password")
                if username: # Log failed attempt
                    log_action(username, "Login Fail")

def draw_case_selection_page():
    st.title("Case Selection")
    st.markdown(f"Welcome, **{st.session_state.username}**! Select a case to begin.")

    if st.sidebar.button("Logout"):
        log_action(st.session_state.username, "Logout")
        st.session_state.logged_in = False
        st.session_state.page = "login"
        del st.session_state.username
        if 'is_admin' in st.session_state:
            del st.session_state.is_admin
        st.rerun()

    if st.session_state.get('is_admin'):
        if st.sidebar.button("Admin Page"):
            st.session_state.page = "admin"
            st.rerun()

    cases = get_cases()
    diagnoses = load_diagnoses()
    user_diagnoses = diagnoses.get(st.session_state.username, {})

    for case in cases:
        is_done = case in user_diagnoses
        bg_color = "#28a745" if is_done else "#6c757d" # Green or Grey
        text_color = "white"

        col_case_name, col_open_button = st.columns([0.7, 0.3]) # Adjust ratios as needed

        with col_case_name:
            st.markdown(
                f'<div style="background-color:{bg_color}; padding:10px; border-radius:5px; color:{text_color}; height: 50px; display: flex; align-items: center;">'
                f'<h3 style="margin:0;">{case}</h3>'
                f'</div>',
                unsafe_allow_html=True
            )
        with col_open_button:
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True) # Spacer to align button
            if st.button("Open", key=f"open_{case}"):
                log_action(st.session_state.username, "Open Case", case=case)
                st.session_state.page = "viewer"
                st.session_state.selected_case = case
                st.session_state.series_progress = {}
                st.rerun()

def increment_slice(current_series, max_slice):
    if st.session_state.series_progress[current_series] < max_slice:
        st.session_state.series_progress[current_series] += 1
        log_action(st.session_state.username, "Change Slice", case=st.session_state.selected_case, series=current_series, details=f"Slice: {st.session_state.series_progress[current_series]}")

def decrement_slice(current_series):
    if st.session_state.series_progress[current_series] > 1:
        st.session_state.series_progress[current_series] -= 1
        log_action(st.session_state.username, "Change Slice", case=st.session_state.selected_case, series=current_series, details=f"Slice: {st.session_state.series_progress[current_series]}")

def draw_viewer_page():
    selected_case = st.session_state.selected_case
    username = st.session_state.username
    st.title(f"Viewing Case: {selected_case}")

    if 'series_progress' not in st.session_state:
        st.session_state.series_progress = {}

    if st.sidebar.button("⬅️ Back to Case Selection"):
        log_action(username, "Back to Selection", case=selected_case)
        st.session_state.page = "case_selection"
        del st.session_state.selected_case
        del st.session_state.series_progress
        st.rerun()
    
    st.sidebar.title("Series Navigation")
    series_list_raw = get_series_for_case(selected_case)
    if not series_list_raw: 
        st.warning(f"No series found for case '{selected_case}'."); return

    series_options = ["-- Please Select a Series --"] + series_list_raw

    if 'last_selected_series' not in st.session_state:
        st.session_state.last_selected_series = None

    try:
        initial_series_index = series_options.index(st.session_state.last_selected_series)
    except ValueError:
        initial_series_index = 0

    selected_series_from_selectbox = st.sidebar.selectbox(
        "Select a Series",
        series_options,
        index=initial_series_index,
        key="series_selectbox"
    )

    current_series = None
    if selected_series_from_selectbox != "-- Please Select a Series --":
        current_series = selected_series_from_selectbox

    if current_series and current_series != st.session_state.last_selected_series:
        log_action(username, "Select Series", case=selected_case, series=current_series)
        st.session_state.last_selected_series = current_series
        st.rerun()
    elif not current_series and st.session_state.last_selected_series:
        st.session_state.last_selected_series = None
        st.rerun()

    if current_series:
        images = get_images_for_series(selected_case, current_series)
        if not images: 
            st.warning(f"No images found for series '{current_series}'."); return

        if current_series not in st.session_state.series_progress:
            st.session_state.series_progress[current_series] = 1

        slice_index = st.session_state.series_progress[current_series]

        st.sidebar.markdown("---")
        st.sidebar.subheader("Slice Navigation")
        
        st.sidebar.button("⬆️ Up", on_click=decrement_slice, args=(current_series,))
        st.sidebar.write(f"Current Slice: {slice_index} / {len(images)}")
        st.sidebar.button("⬇️ Down", on_click=increment_slice, args=(current_series, len(images)))

        st.subheader(f"Viewing: {selected_case} / {current_series}")
        st.image(str(images[slice_index - 1]), width=800)

        st.subheader("Diagnosis")
        diagnoses = load_diagnoses()
        user_diagnoses = diagnoses.get(username, {})
        previous_diagnosis = user_diagnoses.get(selected_case, "")
        diagnosis_text = st.text_area("Enter your diagnosis here:", value=previous_diagnosis, height=70)

        if st.button("Save Diagnosis"):
            if username not in diagnoses:
                diagnoses[username] = {}
            diagnoses[username][selected_case] = diagnosis_text
            save_diagnoses(diagnoses)
            log_action(username, "Save Diagnosis", case=selected_case, details=diagnosis_text)
            st.success("Diagnosis saved!")
            st.session_state.page = "case_selection"
            del st.session_state.selected_case
            del st.session_state.series_progress
            st.rerun()
    else:
        st.info("Please select a series from the sidebar to view images.")

    st.sidebar.markdown("---")
    st.sidebar.subheader("Instructions")
    st.sidebar.markdown("⬆️ Select a series from the dropdown above.")
    st.sidebar.markdown("⬆️⬇️ Use the buttons to navigate slices.")

def draw_admin_page():
    st.title("Admin Page")

    if st.sidebar.button("⬅️ Back to Case Selection"):
        st.session_state.page = "case_selection"
        st.rerun()

    st.subheader("Action Logs")
    log_files = [f for f in LOGS_DIR.iterdir() if f.name.endswith("_action_log.xlsx")]
    if not log_files:
        st.warning("No log files found.")
    else:
        log_filenames = [f.name for f in log_files]
        selected_log = st.selectbox("Select a log file to view:", log_filenames)
        if selected_log:
            log_df = pd.read_excel(LOGS_DIR / selected_log)
            st.dataframe(log_df)

    st.subheader("User List")
    if USERS_FILE.exists():
        users_df = pd.read_excel(USERS_FILE)
        st.dataframe(users_df)
    else:
        st.warning("Users file not found.")

# --- Main App Router ---

initialize_admin_user()

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.page = "login"

if not st.session_state.logged_in:
    draw_login_page()
else:
    if st.session_state.page == "case_selection":
        draw_case_selection_page()
    elif st.session_state.page == "viewer":
        draw_viewer_page()
    elif st.session_state.page == "admin" and st.session_state.get('is_admin'):
        draw_admin_page()
    else:
        st.session_state.page = "case_selection"
        st.rerun()
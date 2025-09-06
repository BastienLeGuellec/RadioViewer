
import streamlit as st
from pathlib import Path
import pandas as pd
from datetime import datetime
import json

# --- Configuration ---
DATA_DIR = Path("data")
USERS_FILE = Path("users.xlsx")
DIAGNOSES_FILE = Path("diagnoses.json")
LOG_FILE = Path("action_log.xlsx")
st.set_page_config(layout="wide", page_title="Radiology Case Viewer")

# --- Logging Function ---
def log_action(username, action, case="", series="", details=""):
    """Appends a log entry to the specified Excel file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    columns=['Timestamp', 'Username', 'Action', 'Case', 'Series', 'Details']
    new_log_entry = pd.DataFrame([[timestamp, username, action, case, series, details]], columns=columns)
    
    try:
        if LOG_FILE.exists():
            log_df = pd.read_excel(LOG_FILE)
            # Ensure columns match, if not, create new file
            if list(log_df.columns) != columns:
                log_df = new_log_entry
            else:
                log_df = pd.concat([log_df, new_log_entry], ignore_index=True)
        else:
            log_df = new_log_entry
        
        log_df.to_excel(LOG_FILE, index=False)

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
                # Reset series/slice tracking when opening a new case
                if 'last_selected_series' in st.session_state: del st.session_state.last_selected_series
                if 'last_slice_index' in st.session_state: del st.session_state.last_slice_index
                st.rerun()

def draw_viewer_page():
    selected_case = st.session_state.selected_case
    username = st.session_state.username
    st.title(f"Viewing Case: {selected_case}")

    # Instructions for diagnosis in main area
    st.info("Enter your diagnosis below.")

    if st.sidebar.button("⬅️ Back to Case Selection"):
        log_action(username, "Back to Selection", case=selected_case)
        st.session_state.page = "case_selection"
        del st.session_state.selected_case
        st.rerun()
    
    st.sidebar.title("Series Navigation")
    series_list_raw = get_series_for_case(selected_case)
    if not series_list_raw: 
        st.warning(f"No series found for case '{selected_case}'."); return

    # Prepend a "Please Select" option
    series_options = ["-- Please Select a Series --"] + series_list_raw

    # Determine initial index for selectbox
    initial_series_index = 0 # Default to "Please Select"

    # If a series was previously selected and is still valid, try to pre-select it
    if 'last_selected_series' in st.session_state and st.session_state.last_selected_series in series_list_raw:
        initial_series_index = series_list_raw.index(st.session_state.last_selected_series) + 1 # +1 because of "Please Select"

    selected_series_from_selectbox = st.sidebar.selectbox(
        "Select a Series",
        series_options,
        index=initial_series_index,
        key="series_selectbox" # Add a key to prevent issues with dynamic options
    )

    # Determine the actual series to use for display
    current_series = None
    if selected_series_from_selectbox != "-- Please Select a Series --":
        current_series = selected_series_from_selectbox

    # Check if the user made a new valid selection via the selectbox
    # Only log if a real series is selected AND it's different from the last logged one
    if current_series and current_series != st.session_state.get('last_selected_series_logged', None):
        log_action(username, "Select Series", case=selected_case, series=current_series)
        st.session_state.last_selected_series_logged = current_series # Update logged state
        st.session_state.last_selected_series = current_series # Update for image display
        st.session_state.last_slice_index = 1 # Reset slice index when series changes
        st.rerun() # Rerun to update image based on new series and reset slice
    elif not current_series and 'last_selected_series_logged' in st.session_state: # If user switches back to "Please Select"
        del st.session_state.last_selected_series_logged
        if 'last_selected_series' in st.session_state: del st.session_state.last_selected_series
        if 'last_slice_index' in st.session_state: del st.session_state.last_slice_index
        st.rerun() # Rerun to clear image

    # Only display image and controls if a series is actually selected
    if current_series:
        images = get_images_for_series(selected_case, current_series)
        if not images: 
            st.warning(f"No images found for series '{current_series}'."); return

        # Ensure last_slice_index is initialized for the current series
        if 'last_slice_index' not in st.session_state or st.session_state.last_slice_index > len(images):
            st.session_state.last_slice_index = 1

        # Slice navigation buttons in sidebar
        st.sidebar.markdown("---")
        st.sidebar.subheader("Slice Navigation")
        if st.sidebar.button("⬆️ Up", key="slice_up_sidebar"):
            if st.session_state.get('last_slice_index', 1) > 1: # Go down in slice number
                st.session_state.last_slice_index -= 1
                log_action(username, "Change Slice", case=selected_case, series=current_series, details=f"Slice: {st.session_state.last_slice_index}")
        
        st.sidebar.write(f"Current Slice: {st.session_state.get('last_slice_index', 1)} / {len(images)}")

        if st.sidebar.button("⬇️ Down", key="slice_down_sidebar"):
            if st.session_state.get('last_slice_index', 1) < len(images): # Go up in slice number
                st.session_state.last_slice_index += 1
                log_action(username, "Change Slice", case=selected_case, series=current_series, details=f"Slice: {st.session_state.last_slice_index}")

        # Image display
        st.subheader(f"Viewing: {selected_case} / {current_series}")
        # Image sizing: Display at a fixed width to maintain consistency
        st.title(f"Viewing Case: {selected_case}")

    # Instructions for diagnosis in main area
    # Removed: st.info("Enter your diagnosis below.")

    if st.sidebar.button("⬅️ Back to Case Selection"):
        log_action(username, "Back to Selection", case=selected_case)
        st.session_state.page = "case_selection"
        del st.session_state.selected_case
        st.rerun()
    
    st.sidebar.title("Series Navigation")
    series_list_raw = get_series_for_case(selected_case)
    if not series_list_raw: 
        st.warning(f"No series found for case '{selected_case}'."); return

    # Prepend a "Please Select" option
    series_options = ["-- Please Select a Series --"] + series_list_raw

    # Determine initial index for selectbox
    initial_series_index = 0 # Default to "Please Select"

    # If a series was previously selected and is still valid, try to pre-select it
    if 'last_selected_series' in st.session_state and st.session_state.last_selected_series in series_list_raw:
        initial_series_index = series_list_raw.index(st.session_state.last_selected_series) + 1 # +1 because of "Please Select"

    selected_series_from_selectbox = st.sidebar.selectbox(
        "Select a Series",
        series_options,
        index=initial_series_index,
        key="series_selectbox" # Add a key to prevent issues with dynamic options
    )

    # Determine the actual series to use for display
    current_series = None
    if selected_series_from_selectbox != "-- Please Select a Series --":
        current_series = selected_series_from_selectbox

    # Check if the user made a new valid selection via the selectbox
    # Only log if a real series is selected AND it's different from the last logged one
    if current_series and current_series != st.session_state.get('last_selected_series_logged', None):
        log_action(username, "Select Series", case=selected_case, series=current_series)
        st.session_state.last_selected_series_logged = current_series # Update logged state
        st.session_state.last_selected_series = current_series # Update for image display
        st.session_state.last_slice_index = 1 # Reset slice index when series changes
        st.rerun() # Rerun to update image based on new series and reset slice
    elif not current_series and 'last_selected_series_logged' in st.session_state: # If user switches back to "Please Select"
        del st.session_state.last_selected_series_logged
        if 'last_selected_series' in st.session_state: del st.session_state.last_selected_series
        if 'last_slice_index' in st.session_state: del st.session_state.last_slice_index
        st.rerun() # Rerun to clear image

    # Only display image and controls if a series is actually selected
    if current_series:
        images = get_images_for_series(selected_case, current_series)
        if not images: 
            st.warning(f"No images found for series '{current_series}'."); return

        # Ensure last_slice_index is initialized for the current series
        if 'last_slice_index' not in st.session_state or st.session_state.last_slice_index > len(images):
            st.session_state.last_slice_index = 1

        # Slice navigation buttons in sidebar
        st.sidebar.markdown("---")
        st.sidebar.subheader("Slice Navigation")
        if st.sidebar.button("⬆️ Up", key="slice_up_sidebar"):
            if st.session_state.get('last_slice_index', 1) > 1: # Go down in slice number
                st.session_state.last_slice_index -= 1
                log_action(username, "Change Slice", case=selected_case, series=current_series, details=f"Slice: {st.session_state.last_slice_index}")
        
        st.sidebar.write(f"Current Slice: {st.session_state.get('last_slice_index', 1)} / {len(images)}")

        if st.sidebar.button("⬇️ Down", key="slice_down_sidebar"):
            if st.session_state.get('last_slice_index', 1) < len(images): # Go up in slice number
                st.session_state.last_slice_index += 1
                log_action(username, "Change Slice", case=selected_case, series=current_series, details=f"Slice: {st.session_state.last_slice_index}")

        # Image display
        st.subheader(f"Viewing: {selected_case} / {current_series}")
        # Image sizing: Display at a fixed width to maintain consistency
def draw_viewer_page():
    selected_case = st.session_state.selected_case
    username = st.session_state.username
    st.title(f"Viewing Case: {selected_case}")

    if st.sidebar.button("⬅️ Back to Case Selection"):
        log_action(username, "Back to Selection", case=selected_case)
        st.session_state.page = "case_selection"
        del st.session_state.selected_case
        st.rerun()
    
    st.sidebar.title("Series Navigation")
    series_list_raw = get_series_for_case(selected_case)
    if not series_list_raw: 
        st.warning(f"No series found for case '{selected_case}'."); return

    # Prepend a "Please Select" option
    series_options = ["-- Please Select a Series --"] + series_list_raw

    # Determine initial index for selectbox
    initial_series_index = 0 # Default to "Please Select"

    # If a series was previously selected and is still valid, try to pre-select it
    if 'last_selected_series' in st.session_state and st.session_state.last_selected_series in series_list_raw:
        initial_series_index = series_list_raw.index(st.session_state.last_selected_series) + 1 # +1 because of "Please Select"

    selected_series_from_selectbox = st.sidebar.selectbox(
        "Select a Series",
        series_options,
        index=initial_series_index,
        key="series_selectbox" # Add a key to prevent issues with dynamic options
    )

    # Determine the actual series to use for display
    current_series = None
    if selected_series_from_selectbox != "-- Please Select a Series --":
        current_series = selected_series_from_selectbox

    # Check if the user made a new valid selection via the selectbox
    # Only log if a real series is selected AND it's different from the last logged one
    if current_series and current_series != st.session_state.get('last_selected_series_logged', None):
        log_action(username, "Select Series", case=selected_case, series=current_series)
        st.session_state.last_selected_series_logged = current_series # Update logged state
        st.session_state.last_selected_series = current_series # Update for image display
        st.session_state.last_slice_index = 1 # Reset slice index when series changes
        st.rerun() # Rerun to update image based on new series and reset slice
    elif not current_series and 'last_selected_series_logged' in st.session_state: # If user switches back to "Please Select"
        del st.session_state.last_selected_series_logged
        if 'last_selected_series' in st.session_state: del st.session_state.last_selected_series
        if 'last_slice_index' in st.session_state: del st.session_state.last_slice_index
        st.rerun() # Rerun to clear image

    # Only display image and controls if a series is actually selected
    if current_series:
        images = get_images_for_series(selected_case, current_series)
        if not images: 
            st.warning(f"No images found for series '{current_series}'."); return

        # Ensure last_slice_index is initialized for the current series
        if 'last_slice_index' not in st.session_state or st.session_state.last_slice_index > len(images):
            st.session_state.last_slice_index = 1

        # Slice navigation buttons in sidebar
        st.sidebar.markdown("---")
        st.sidebar.subheader("Slice Navigation")
        if st.sidebar.button("⬆️ Up", key="slice_up_sidebar"):
            if st.session_state.get('last_slice_index', 1) > 1: # Go down in slice number
                st.session_state.last_slice_index -= 1
                log_action(username, "Change Slice", case=selected_case, series=current_series, details=f"Slice: {st.session_state.last_slice_index}")
        
        st.sidebar.write(f"Current Slice: {st.session_state.get('last_slice_index', 1)} / {len(images)}")

        if st.sidebar.button("⬇️ Down", key="slice_down_sidebar"):
            if st.session_state.get('last_slice_index', 1) < len(images): # Go up in slice number
                st.session_state.last_slice_index += 1
                log_action(username, "Change Slice", case=selected_case, series=current_series, details=f"Slice: {st.session_state.last_slice_index}")

        # Image display
        st.subheader(f"Viewing: {selected_case} / {current_series}")
        # Image sizing: Display at a fixed width to maintain consistency
        st.image(str(images[st.session_state.get('last_slice_index', 1) - 1]), width=800) # Fixed width for consistency

        st.subheader("Diagnosis")
        diagnoses = load_diagnoses()
        user_diagnoses = diagnoses.get(username, {})
        previous_diagnosis = user_diagnoses.get(selected_case, "")
        diagnosis_text = st.text_area("Enter your diagnosis here:", value=previous_diagnosis, height=70) # Smaller height

        if st.button("Save Diagnosis"):
            if username not in diagnoses:
                diagnoses[username] = {}
            diagnoses[username][selected_case] = diagnosis_text
            save_diagnoses(diagnoses)
            log_action(username, "Save Diagnosis", case=selected_case, details=diagnosis_text)
            st.success("Diagnosis saved!")
            st.session_state.page = "case_selection"
            del st.session_state.selected_case
            st.rerun()
    else:
        st.info("Please select a series from the sidebar to view images.")

    # Instructions at the bottom of the sidebar
    st.sidebar.markdown("---") # Separator
    st.sidebar.subheader("Instructions")
    st.sidebar.markdown("⬆️ Select a series from the dropdown above.")
    st.sidebar.markdown("⬆️⬇️ Use the buttons to navigate slices.")

    st.subheader("Diagnosis")
    diagnoses = load_diagnoses()
    user_diagnoses = diagnoses.get(username, {})
    previous_diagnosis = user_diagnoses.get(selected_case, "")
    diagnosis_text = st.text_area("Enter your diagnosis here:", value=previous_diagnosis, height=70) # Smaller height

    if st.button("Save Diagnosis"):
        if username not in diagnoses:
            diagnoses[username] = {}
        diagnoses[username][selected_case] = diagnosis_text
        save_diagnoses(diagnoses)
        log_action(username, "Save Diagnosis", case=selected_case, details=diagnosis_text)
        st.success("Diagnosis saved!")
        st.session_state.page = "case_selection"
        del st.session_state.selected_case
        st.rerun()



# --- Main App Router ---

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
    else:
        st.session_state.page = "case_selection"
        st.rerun()
